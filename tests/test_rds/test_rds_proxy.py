import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

DEFAULT_REGION = "us-west-2"


@mock_aws
def test_create_db_proxy():
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    vpc_id = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    subnet_id_2 = ec2_client.create_subnet(CidrBlock="10.0.2.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    resp = rds_client.create_db_proxy(
        DBProxyName="testrdsproxy",
        EngineFamily="MYSQL",
        Auth=[
            {
                "Description": "Test Description",
                "UserName": "Test Username",
                "AuthScheme": "SECRETS",
                "SecretArn": "TestSecretARN",
                "IAMAuth": "ENABLED",
                "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
            },
        ],
        RoleArn="TestArn",
        VpcSubnetIds=[subnet_id, subnet_id_2],
        RequireTLS=True,
        Tags=[{"Key": "TestKey", "Value": "TestValue"}],
    )
    db_proxy = resp["DBProxy"]
    assert db_proxy["DBProxyName"] == "testrdsproxy"
    assert (
        db_proxy["DBProxyArn"]
        == f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:db-proxy:testrdsproxy"
    )
    assert db_proxy["Status"] == "availible"
    assert db_proxy["EngineFamily"] == "MYSQL"
    assert db_proxy["VpcId"] == vpc_id
    assert db_proxy["VpcSecurityGroupIds"] == []
    assert db_proxy["VpcSubnetIds"] == [subnet_id, subnet_id_2]
    assert db_proxy["Auth"] == [
        {
            "UserName": "Test Username",
            "AuthScheme": "SECRETS",
            "SecretArn": "TestSecretARN",
            "IAMAuth": "ENABLED",
            "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
        }
    ]
    assert db_proxy["RoleArn"] == "TestArn"
    assert db_proxy["RequireTLS"] is True
    assert db_proxy["IdleClientTimeout"] == 1800
    assert db_proxy["DebugLogging"] is False


@mock_aws
def test_describe_db_proxies():
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    vpc_id = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    subnet_id_2 = ec2_client.create_subnet(CidrBlock="10.0.2.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    rds_client.create_db_proxy(
        DBProxyName="testrdsproxydescribe",
        EngineFamily="MYSQL",
        Auth=[
            {
                "Description": "Test Description",
                "UserName": "Test Username",
                "AuthScheme": "SECRETS",
                "SecretArn": "TestSecretARN",
                "IAMAuth": "ENABLED",
                "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
            },
        ],
        RoleArn="TestArn",
        VpcSubnetIds=[subnet_id, subnet_id_2],
        RequireTLS=True,
        Tags=[
            {"Key": "TestKey", "Value": "TestValue"},
            {"Key": "aaa", "Value": "bbb"},
        ],
    )
    response = rds_client.describe_db_proxies(DBProxyName="testrdsproxydescribe")
    db_proxy = response["DBProxies"][0]
    assert db_proxy["DBProxyName"] == "testrdsproxydescribe"
    assert (
        db_proxy["DBProxyArn"]
        == f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:db-proxy:testrdsproxydescribe"
    )
    assert db_proxy["Status"] == "availible"
    assert db_proxy["EngineFamily"] == "MYSQL"
    assert db_proxy["VpcId"] == vpc_id
    assert db_proxy["VpcSecurityGroupIds"] == []
    assert db_proxy["VpcSubnetIds"] == [subnet_id, subnet_id_2]
    assert db_proxy["Auth"] == [
        {
            "UserName": "Test Username",
            "AuthScheme": "SECRETS",
            "SecretArn": "TestSecretARN",
            "IAMAuth": "ENABLED",
            "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
        }
    ]
    assert db_proxy["RoleArn"] == "TestArn"
    assert db_proxy["RequireTLS"] is True
    assert db_proxy["IdleClientTimeout"] == 1800
    assert db_proxy["DebugLogging"] is False


@mock_aws
def test_list_tags_db_proxy():
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    vpc_id = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    subnet_id_2 = ec2_client.create_subnet(CidrBlock="10.0.2.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    resp = rds_client.create_db_proxy(
        DBProxyName="testrdsproxydescribe",
        EngineFamily="MYSQL",
        Auth=[
            {
                "Description": "Test Description",
                "UserName": "Test Username",
                "AuthScheme": "SECRETS",
                "SecretArn": "TestSecretARN",
                "IAMAuth": "ENABLED",
                "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
            },
        ],
        RoleArn="TestArn",
        VpcSubnetIds=[subnet_id, subnet_id_2],
        RequireTLS=True,
        Tags=[
            {"Key": "TestKey", "Value": "TestValue"},
            {"Key": "aaa", "Value": "bbb"},
        ],
    )
    arn = resp["DBProxy"]["DBProxyArn"]
    resp = rds_client.list_tags_for_resource(ResourceName=arn)
    assert resp["TagList"] == [
        {"Value": "TestValue", "Key": "TestKey"},
        {"Value": "bbb", "Key": "aaa"},
    ]


@mock_aws
def test_create_db_proxy_invalid_subnet():
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    vpc_id = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    vpc_id_2 = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    subnet_id_2 = ec2_client.create_subnet(CidrBlock="10.0.2.0/24", VpcId=vpc_id_2)[
        "Subnet"
    ]["SubnetId"]
    with pytest.raises(ClientError) as ex:
        rds_client.create_db_proxy(
            DBProxyName="testrdsproxy",
            EngineFamily="MYSQL",
            Auth=[
                {
                    "Description": "Test Description",
                    "UserName": "Test Username",
                    "AuthScheme": "SECRETS",
                    "SecretArn": "TestSecretARN",
                    "IAMAuth": "ENABLED",
                    "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
                },
            ],
            RoleArn="TestArn",
            VpcSubnetIds=[subnet_id, subnet_id_2],
            RequireTLS=True,
            Tags=[{"Key": "TestKey", "Value": "TestValue"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidSubnet"


@mock_aws
def test_create_db_proxy_duplicate_name():
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    ec2_client = boto3.client("ec2", region_name=DEFAULT_REGION)
    vpc_id = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_id = ec2_client.create_subnet(CidrBlock="10.0.1.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    subnet_id_2 = ec2_client.create_subnet(CidrBlock="10.0.2.0/24", VpcId=vpc_id)[
        "Subnet"
    ]["SubnetId"]
    rds_client.create_db_proxy(
        DBProxyName="testrdsproxy",
        EngineFamily="MYSQL",
        Auth=[
            {
                "Description": "Test Description",
                "UserName": "Test Username",
                "AuthScheme": "SECRETS",
                "SecretArn": "TestSecretARN",
                "IAMAuth": "ENABLED",
                "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
            },
        ],
        RoleArn="TestArn",
        VpcSubnetIds=[subnet_id, subnet_id_2],
        RequireTLS=True,
        Tags=[{"Key": "TestKey", "Value": "TestValue"}],
    )
    with pytest.raises(ClientError) as ex:
        rds_client.create_db_proxy(
            DBProxyName="testrdsproxy",
            EngineFamily="MYSQL",
            Auth=[
                {
                    "Description": "Test Description",
                    "UserName": "Test Username",
                    "AuthScheme": "SECRETS",
                    "SecretArn": "TestSecretARN",
                    "IAMAuth": "ENABLED",
                    "ClientPasswordAuthType": "MYSQL_NATIVE_PASSWORD",
                },
            ],
            RoleArn="TestArn",
            VpcSubnetIds=[subnet_id, subnet_id_2],
            RequireTLS=True,
            Tags=[{"Key": "TestKey", "Value": "TestValue"}],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "DBProxyAlreadyExistsFault"
    assert (
        err["Message"]
        == "Cannot create the DBProxy because a DBProxy with the identifier testrdsproxy already exists."
    )


@mock_aws
def test_describe_db_proxies_not_found():
    rds_client = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        rds_client.describe_db_proxies(DBProxyName="testrdsproxydescribe")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBProxyNotFoundFault"
    assert (
        err["Message"]
        == "The specified proxy name testrdsproxydescribe doesn't correspond to a proxy owned by your Amazon Web Services account in the specified Amazon Web Services Region."
    )
