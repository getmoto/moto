import boto3
import json
import sure  # noqa
from moto import mock_cloudformation, mock_ec2, mock_rds2


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
