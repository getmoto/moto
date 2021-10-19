import boto3
import json
import sure  # noqa # pylint: disable=unused-import
from moto import mock_cloudformation, mock_ec2, mock_rds2
from tests.test_cloudformation.fixtures import rds_mysql_with_db_parameter_group
from tests.test_cloudformation.fixtures import rds_mysql_with_read_replica


@mock_ec2
@mock_rds2
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
    response.should.have.length_of(1)

    created_subnet = response[0]
    created_subnet.should.have.key("DBSubnetGroupName").equal("subnetgroupname")
    created_subnet.should.have.key("DBSubnetGroupDescription").equal("subnetgroupdesc")
    created_subnet.should.have.key("VpcId").equal(vpc["VpcId"])


@mock_ec2
@mock_rds2
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
    }
    template_json = json.dumps(template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    summaries = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]

    db_instance_identifier = summaries[0]["PhysicalResourceId"]
    resp = rds.describe_db_instances()["DBInstances"]
    resp.should.have.length_of(1)

    created = resp[0]
    created["DBInstanceIdentifier"].should.equal(db_instance_identifier)
    created["Engine"].should.equal("mysql")
    created["DBInstanceStatus"].should.equal("available")


@mock_ec2
@mock_rds2
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
    result.should.have.length_of(1)

    created = result[0]
    created["DBSecurityGroupDescription"].should.equal("my sec group")


@mock_cloudformation
@mock_ec2
@mock_rds2
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
                ("DBInstanceIdentifier", "master_db"),
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
    db_parameter_groups["DBParameterGroups"].should.have.length_of(1)
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

    found_cloudformation_set_parameter.should.equal(True)


@mock_cloudformation
@mock_ec2
@mock_rds2
def test_rds_mysql_with_read_replica():
    ec2_conn = boto3.client("ec2", region_name="us-west-1")
    ec2_conn.create_security_group(
        GroupName="application", Description="Our Application Group"
    )

    template_json = json.dumps(rds_mysql_with_read_replica.template)
    cf = boto3.client("cloudformation", "us-west-1")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[
            {"ParameterKey": "DBInstanceIdentifier", "ParameterValue": "master_db"},
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

    primary = rds.describe_db_instances(DBInstanceIdentifier="master_db")[
        "DBInstances"
    ][0]
    primary.should.have.key("MasterUsername").equal("my_user")
    primary.should.have.key("AllocatedStorage").equal(20)
    primary.should.have.key("DBInstanceClass").equal("db.m1.medium")
    primary.should.have.key("MultiAZ").equal(True)
    primary.should.have.key("ReadReplicaDBInstanceIdentifiers").being.length_of(1)
    replica_id = primary["ReadReplicaDBInstanceIdentifiers"][0]

    replica = rds.describe_db_instances(DBInstanceIdentifier=replica_id)["DBInstances"][
        0
    ]
    replica.should.have.key("DBInstanceClass").equal("db.m1.medium")

    security_group_name = primary["DBSecurityGroups"][0]["DBSecurityGroupName"]
    security_group = rds.describe_db_security_groups(
        DBSecurityGroupName=security_group_name
    )["DBSecurityGroups"][0]
    security_group["EC2SecurityGroups"][0]["EC2SecurityGroupName"].should.equal(
        "application"
    )


@mock_cloudformation
@mock_ec2
@mock_rds2
def test_rds_mysql_with_read_replica_in_vpc():
    template_json = json.dumps(rds_mysql_with_read_replica.template)
    cf = boto3.client("cloudformation", "eu-central-1")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[
            {"ParameterKey": "DBInstanceIdentifier", "ParameterValue": "master_db"},
            {"ParameterKey": "DBName", "ParameterValue": "my_db"},
            {"ParameterKey": "DBUser", "ParameterValue": "my_user"},
            {"ParameterKey": "DBPassword", "ParameterValue": "my_password"},
            {"ParameterKey": "DBAllocatedStorage", "ParameterValue": "20"},
            {"ParameterKey": "DBInstanceClass", "ParameterValue": "db.m1.medium"},
            {"ParameterKey": "MultiAZ", "ParameterValue": "true"},
        ],
    )

    rds = boto3.client("rds", region_name="eu-central-1")
    primary = rds.describe_db_instances(DBInstanceIdentifier="master_db")[
        "DBInstances"
    ][0]

    subnet_group_name = primary["DBSubnetGroup"]["DBSubnetGroupName"]
    subnet_group = rds.describe_db_subnet_groups(DBSubnetGroupName=subnet_group_name)[
        "DBSubnetGroups"
    ][0]
    subnet_group.should.have.key("DBSubnetGroupDescription").equal("my db subnet group")
