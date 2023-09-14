import json

import boto3

from moto import mock_cloudformation, mock_ec2, mock_rds
from tests.test_cloudformation.fixtures import rds_mysql_with_db_parameter_group
from tests.test_cloudformation.fixtures import rds_mysql_with_read_replica


@mock_ec2
@mock_rds
@mock_cloudformation
def test_create_subnetgroup_via_cf():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    rds = boto3.client("rds", region_name="us-west-2")
    cf = boto3.client("cloudformation", region_name="us-west-2")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "subnet": {
                "Type": "AWS::RDS::DBSubnetGroup",
                "Properties": {
                    "DBSubnetGroupName": "subnetgroupname",
                    "DBSubnetGroupDescription": "subnetgroupdesc",
                    "SubnetIds": [subnet["SubnetId"]],
                },
            }
        },
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    response = rds.describe_db_subnet_groups()["DBSubnetGroups"]
    assert len(response) == 1

    created_subnet = response[0]
    assert created_subnet["DBSubnetGroupName"] == "subnetgroupname"
    assert created_subnet["DBSubnetGroupDescription"] == "subnetgroupdesc"
    assert created_subnet["VpcId"] == vpc["VpcId"]


@mock_ec2
@mock_rds
@mock_cloudformation
def test_create_dbinstance_via_cf():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")

    rds = boto3.client("rds", region_name="us-west-2")
    cf = boto3.client("cloudformation", region_name="us-west-2")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "db": {
                "Type": "AWS::RDS::DBInstance",
                "Properties": {
                    "Port": 3307,
                    "Engine": "mysql",
                    # Required - throws exception when describing an instance without tags
                    "Tags": [],
                },
            }
        },
        "Outputs": {
            "db_address": {"Value": {"Fn::GetAtt": ["db", "Endpoint.Address"]}},
            "db_port": {"Value": {"Fn::GetAtt": ["db", "Endpoint.Port"]}},
        },
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    summaries = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]

    db_instance_identifier = summaries[0]["PhysicalResourceId"]
    resp = rds.describe_db_instances()["DBInstances"]
    assert len(resp) == 1

    created = resp[0]
    assert created["DBInstanceIdentifier"] == db_instance_identifier
    assert created["Engine"] == "mysql"
    assert created["DBInstanceStatus"] == "available"

    # Verify the stack outputs are correct
    o = _get_stack_outputs(cf, stack_name="test_stack")
    assert o["db_address"] == (
        f"{db_instance_identifier}.aaaaaaaaaa.us-west-2.rds.amazonaws.com"
    )
    assert o["db_port"] == "3307"


@mock_ec2
@mock_rds
@mock_cloudformation
def test_create_dbsecuritygroup_via_cf():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")

    rds = boto3.client("rds", region_name="us-west-2")
    cf = boto3.client("cloudformation", region_name="us-west-2")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "db": {
                "Type": "AWS::RDS::DBSecurityGroup",
                "Properties": {"GroupDescription": "my sec group"},
            }
        },
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    result = rds.describe_db_security_groups()["DBSecurityGroups"]
    assert len(result) == 1

    created = result[0]
    assert created["DBSecurityGroupDescription"] == "my sec group"


@mock_cloudformation
@mock_ec2
@mock_rds
def test_rds_db_parameter_groups():
    ec2_conn = boto3.client("ec2", region_name="us-west-1")
    ec2_conn.create_security_group(
        GroupName="application", Description="Our Application Group"
    )

    template_json = json.dumps(rds_mysql_with_db_parameter_group.template)
    cf_conn = boto3.client("cloudformation", "us-west-1")
    cf_conn.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[
            {"ParameterKey": key, "ParameterValue": value}
            for key, value in [
                ("DBInstanceIdentifier", "master-db"),
                ("DBName", "my_db"),
                ("DBUser", "my_user"),
                ("DBPassword", "my_password"),
                ("DBAllocatedStorage", "20"),
                ("DBInstanceClass", "db.m1.medium"),
                ("EC2SecurityGroup", "application"),
                ("MultiAZ", "true"),
            ]
        ],
    )

    rds_conn = boto3.client("rds", region_name="us-west-1")

    db_parameter_groups = rds_conn.describe_db_parameter_groups()
    assert len(db_parameter_groups["DBParameterGroups"]) == 1
    db_parameter_group_name = db_parameter_groups["DBParameterGroups"][0][
        "DBParameterGroupName"
    ]

    found_cloudformation_set_parameter = False
    for db_parameter in rds_conn.describe_db_parameters(
        DBParameterGroupName=db_parameter_group_name
    )["Parameters"]:
        if (
            db_parameter["ParameterName"] == "BACKLOG_QUEUE_LIMIT"
            and db_parameter["ParameterValue"] == "2048"
        ):
            found_cloudformation_set_parameter = True

    assert found_cloudformation_set_parameter is True


@mock_cloudformation
@mock_ec2
@mock_rds
def test_rds_mysql_with_read_replica():
    ec2_conn = boto3.client("ec2", region_name="us-west-1")
    ec2_conn.create_security_group(
        GroupName="application", Description="Our Application Group"
    )

    template_json = json.dumps(rds_mysql_with_read_replica.template)
    cf = boto3.client("cloudformation", "us-west-1")
    db_identifier = "master-db"
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[
            {"ParameterKey": "DBInstanceIdentifier", "ParameterValue": db_identifier},
            {"ParameterKey": "DBName", "ParameterValue": "my_db"},
            {"ParameterKey": "DBUser", "ParameterValue": "my_user"},
            {"ParameterKey": "DBPassword", "ParameterValue": "my_password"},
            {"ParameterKey": "DBAllocatedStorage", "ParameterValue": "20"},
            {"ParameterKey": "DBInstanceClass", "ParameterValue": "db.m1.medium"},
            {"ParameterKey": "EC2SecurityGroup", "ParameterValue": "application"},
            {"ParameterKey": "MultiAZ", "ParameterValue": "true"},
        ],
    )

    rds = boto3.client("rds", region_name="us-west-1")

    primary = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)[
        "DBInstances"
    ][0]
    assert primary["MasterUsername"] == "my_user"
    assert primary["AllocatedStorage"] == 20
    assert primary["DBInstanceClass"] == "db.m1.medium"
    assert primary["MultiAZ"]
    assert len(primary["ReadReplicaDBInstanceIdentifiers"]) == 1
    replica_id = primary["ReadReplicaDBInstanceIdentifiers"][0]

    replica = rds.describe_db_instances(DBInstanceIdentifier=replica_id)["DBInstances"][
        0
    ]
    assert replica["DBInstanceClass"] == "db.m1.medium"

    security_group_name = primary["DBSecurityGroups"][0]["DBSecurityGroupName"]
    security_group = rds.describe_db_security_groups(
        DBSecurityGroupName=security_group_name
    )["DBSecurityGroups"][0]
    assert (
        security_group["EC2SecurityGroups"][0]["EC2SecurityGroupName"] == "application"
    )


@mock_cloudformation
@mock_ec2
@mock_rds
def test_rds_mysql_with_read_replica_in_vpc():
    template_json = json.dumps(rds_mysql_with_read_replica.template)
    cf = boto3.client("cloudformation", "eu-central-1")
    db_identifier = "master-db"
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[
            {"ParameterKey": "DBInstanceIdentifier", "ParameterValue": db_identifier},
            {"ParameterKey": "DBName", "ParameterValue": "my_db"},
            {"ParameterKey": "DBUser", "ParameterValue": "my_user"},
            {"ParameterKey": "DBPassword", "ParameterValue": "my_password"},
            {"ParameterKey": "DBAllocatedStorage", "ParameterValue": "20"},
            {"ParameterKey": "DBInstanceClass", "ParameterValue": "db.m1.medium"},
            {"ParameterKey": "MultiAZ", "ParameterValue": "true"},
        ],
    )

    rds = boto3.client("rds", region_name="eu-central-1")
    primary = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)[
        "DBInstances"
    ][0]

    subnet_group_name = primary["DBSubnetGroup"]["DBSubnetGroupName"]
    subnet_group = rds.describe_db_subnet_groups(DBSubnetGroupName=subnet_group_name)[
        "DBSubnetGroups"
    ][0]
    assert subnet_group["DBSubnetGroupDescription"] == "my db subnet group"


@mock_ec2
@mock_rds
@mock_cloudformation
def test_delete_dbinstance_via_cf():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")

    rds = boto3.client("rds", region_name="us-west-2")
    cf = boto3.client("cloudformation", region_name="us-west-2")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "db": {
                "Type": "AWS::RDS::DBInstance",
                "Properties": {
                    "Port": 3307,
                    "Engine": "mysql",
                    # Required - throws exception when describing an instance without tags
                    "Tags": [],
                },
            }
        },
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    resp = rds.describe_db_instances()["DBInstances"]
    assert len(resp) == 1

    cf.delete_stack(StackName="test_stack")

    resp = rds.describe_db_instances()["DBInstances"]
    assert len(resp) == 0


def _get_stack_outputs(cf_client, stack_name):
    """Returns the outputs for the first entry in describe_stacks."""
    stack_description = cf_client.describe_stacks(StackName=stack_name)["Stacks"][0]
    return {
        output["OutputKey"]: output["OutputValue"]
        for output in stack_description["Outputs"]
    }
