import json
from time import sleep
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import allow_aws_request

from . import DEFAULT_REGION

ASSUME_ROLE_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "rds.amazonaws.com"},
            "Action": "sts:AssumeRole",
        }
    ],
}


@pytest.fixture(scope="module")
def mockaws():
    if allow_aws_request():
        yield
    else:
        with mock_aws():
            yield


@pytest.fixture(scope="module")
def secrets_arn():
    client = boto3.client("secretsmanager", DEFAULT_REGION)
    secret_name = f"moto-test-{str(uuid4())[0:6]}"

    try:
        secret = client.create_secret(Name=secret_name, SecretString="ss")
        yield secret["ARN"]
    finally:
        client.delete_secret(SecretId=secret_name)


@pytest.fixture(scope="module")
def vpc_id(mockaws):
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    _vpc_id = None
    try:
        _vpc_id = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
        yield _vpc_id
    finally:
        ec2_client.delete_vpc(VpcId=_vpc_id)


@pytest.fixture(scope="module")
def subnet_id1(vpc_id):
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    try:
        subnet = ec2_client.create_subnet(
            CidrBlock="10.0.1.0/24", VpcId=vpc_id, AvailabilityZone="us-east-1a"
        )
        subnet_id = subnet["Subnet"]["SubnetId"]
        yield subnet_id
    finally:
        ec2_client.delete_subnet(SubnetId=subnet_id)


@pytest.fixture(scope="module")
def subnet_id2(vpc_id):
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    try:
        subnet = ec2_client.create_subnet(
            CidrBlock="10.0.2.0/24", VpcId=vpc_id, AvailabilityZone="us-east-1b"
        )
        subnet_id = subnet["Subnet"]["SubnetId"]
        yield subnet_id
    finally:
        ec2_client.delete_subnet(SubnetId=subnet_id)


@pytest.fixture(scope="module")
def role_arn(mockaws):
    role_name = f"moto-test-{str(uuid4())[0:6]}"
    iam = boto3.client("iam", region_name=DEFAULT_REGION)
    try:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(ASSUME_ROLE_POLICY),
        )["Role"]
        yield role["Arn"]
    finally:
        iam.delete_role(RoleName=role_name)


@pytest.fixture(scope="module")
def proxy_name(subnet_id1, subnet_id2, role_arn, secrets_arn):
    name = f"moto-test-{str(uuid4())[0:6]}"
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    proxy_creation_succeeded = False
    try:
        resp = rds_client.create_db_proxy(
            DBProxyName=name,
            EngineFamily="POSTGRESQL",
            Auth=[
                {
                    # "UserName": "user1",
                    # "AuthScheme": "SECRETS",
                    "IAMAuth": "DISABLED",
                    "SecretArn": secrets_arn,
                }
            ],
            RoleArn=role_arn,
            VpcSubnetIds=[subnet_id1, subnet_id2],
        )
        status = resp["DBProxy"]["Status"]
        while status.lower() == "creating":
            sleep(5)
            status = rds_client.describe_db_proxies(DBProxyName=name)["DBProxies"][0][
                "Status"
            ]
        proxy_creation_succeeded = True

        yield name
    finally:
        if proxy_creation_succeeded:
            rds_client.delete_db_proxy(DBProxyName=name)
            deleted = False
            while not deleted:
                try:
                    rds_client.describe_db_proxies(DBProxyName=name)
                    sleep(10)
                except (ClientError, IndexError):
                    deleted = True


@pytest.fixture(scope="module")
def db_cluster_id(mockaws):
    cluster_name = f"moto-test-{str(uuid4())[0:6]}"
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    cluster_creation_succeeded = False
    try:
        cluster_id = rds_client.create_db_cluster(
            DBClusterIdentifier=cluster_name,
            Engine="aurora-postgresql",
            MasterUsername="root",
            MasterUserPassword="hunter21",
        )["DBCluster"]["DBClusterIdentifier"]
        rds_client.get_waiter("db_cluster_available").wait(
            DBClusterIdentifier=cluster_id
        )
        cluster_creation_succeeded = True
        yield cluster_id
    finally:
        if cluster_creation_succeeded:
            rds_client.delete_db_cluster(
                DBClusterIdentifier=cluster_id, SkipFinalSnapshot=True
            )


def test_default_proxy_targets(account_id, proxy_name):
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    resp = rds_client.describe_db_proxy_targets(DBProxyName=proxy_name)

    assert resp["Targets"] == []

    groups = rds_client.describe_db_proxy_target_groups(
        DBProxyName=proxy_name,
        TargetGroupName="default",
    )["TargetGroups"]
    assert len(groups) == 1
    groups[0].pop("CreatedDate")
    groups[0].pop("UpdatedDate")
    target_group_arn = groups[0].pop("TargetGroupArn")
    assert target_group_arn.startswith(
        f"arn:aws:rds:{DEFAULT_REGION}:{account_id}:target-group:prx-tg-"
    )  # 17 more chars (lowercase + digits)
    assert groups[0] == {
        "DBProxyName": proxy_name,
        "TargetGroupName": "default",
        "IsDefault": True,
        "Status": "available",
        "ConnectionPoolConfig": {
            "MaxConnectionsPercent": 100,
            "MaxIdleConnectionsPercent": 50,
            "ConnectionBorrowTimeout": 120,
            "SessionPinningFilters": [],
        },
    }


def test_register_db_proxy(account_id, proxy_name, db_cluster_id):
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)

    resp = rds_client.register_db_proxy_targets(
        DBProxyName=proxy_name,
        DBClusterIdentifiers=[db_cluster_id],
    )["DBProxyTargets"]
    resp[0].pop("Endpoint", None)
    assert resp == [
        {
            "RdsResourceId": db_cluster_id,
            "Port": 5432,
            "Type": "TRACKED_CLUSTER",
            "TargetHealth": {"State": "REGISTERING"},
        }
    ]

    resp = rds_client.describe_db_proxy_targets(DBProxyName=proxy_name)["Targets"]
    resp[0].pop("Endpoint", None)
    resp[0].pop("TargetHealth", None)
    assert resp == [
        {"RdsResourceId": db_cluster_id, "Port": 5432, "Type": "TRACKED_CLUSTER"}
    ]

    rds_client.deregister_db_proxy_targets(
        DBProxyName=proxy_name,
        DBClusterIdentifiers=[db_cluster_id],
    )

    resp = rds_client.describe_db_proxy_targets(DBProxyName=proxy_name)
    assert resp["Targets"] == []


def test_modify_group(proxy_name):
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)

    rds_client.modify_db_proxy_target_group(
        TargetGroupName="default",
        DBProxyName=proxy_name,
        ConnectionPoolConfig={
            "MaxConnectionsPercent": 27,
            "SessionPinningFilters": ["filter1"],
        },
    )

    group = rds_client.describe_db_proxy_target_groups(
        DBProxyName=proxy_name,
        TargetGroupName="default",
    )["TargetGroups"][0]
    assert group["ConnectionPoolConfig"]["MaxConnectionsPercent"] == 27
    assert group["ConnectionPoolConfig"]["MaxIdleConnectionsPercent"] == 13
    assert group["ConnectionPoolConfig"]["SessionPinningFilters"] == ["filter1"]
