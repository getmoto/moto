import boto3
import json
import sure  # noqa
from moto import mock_cloudformation, mock_ec2
from tests import EXAMPLE_AMI_ID
from string import Template
from uuid import uuid4
from .test_instances import retrieve_all_instances


SEC_GROUP_INGRESS = Template(
    """{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "AWS CloudFormation Template to create an EC2 instance",
    "Parameters": {
        "VPCId": {
            "Type": "String",
            "Description": "The VPC ID",
            "AllowedPattern": "^vpc-[a-zA-Z0-9]*"
        }
    },
    "Resources": {
        "SecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "Test VPC security group",
                "GroupName": $group_name,
                "VpcId": {
                    "Ref": "VPCId"
                }
            }
        },
        "SSHIngressRule": {
            "Type": "AWS::EC2::SecurityGroupIngress",
            "Properties": {
                "CidrIp": "10.0.0.0/8",
                "Description": "Allow SSH traffic from 10.0.0.0/8",
                "FromPort": 22,
                "ToPort": 22,
                "GroupId": {
                    "Fn::GetAtt": [
                        "SecurityGroup",
                        "GroupId"
                    ]
                },
                "IpProtocol": "tcp"
            }
        }
    }
}
"""
)


SEC_GROUP_INGRESS_WITHOUT_DESC = Template(
    """{
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "AWS CloudFormation Template to create an EC2 instance",
    "Parameters": {
        "VPCId": {
            "Type": "String",
            "Description": "The VPC ID",
            "AllowedPattern": "^vpc-[a-zA-Z0-9]*"
        }
    },
    "Resources": {
        "SecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "Test VPC security group",
                "GroupName": "$group_name",
                "VpcId": {
                    "Ref": "VPCId"
                }
            }
        },
        "SSHIngressRule": {
            "Type": "AWS::EC2::SecurityGroupIngress",
            "Properties": {
                "CidrIp": "10.0.0.0/8",
                "FromPort": 22,
                "ToPort": 22,
                "GroupId": {
                    "Fn::GetAtt": [
                        "SecurityGroup",
                        "GroupId"
                    ]
                },
                "IpProtocol": "tcp"
            }
        }
    }
}
"""
)

SEC_GROUP_SOURCE = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "my-security-group": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {"GroupDescription": "My other group"},
        },
        "Ec2Instance2": {
            "Type": "AWS::EC2::Instance",
            "Properties": {
                "SecurityGroups": [{"Ref": "InstanceSecurityGroup"}],
                "ImageId": EXAMPLE_AMI_ID,
            },
        },
        "InstanceSecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "My security group",
                "Tags": [{"Key": "bar", "Value": "baz"}],
                "SecurityGroupIngress": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": "22",
                        "ToPort": "22",
                        "CidrIp": "123.123.123.123/32",
                    },
                    {
                        "IpProtocol": "tcp",
                        "FromPort": "80",
                        "ToPort": "8000",
                        "SourceSecurityGroupId": {"Ref": "my-security-group"},
                    },
                ],
            },
        },
    },
}


@mock_cloudformation
@mock_ec2
def test_security_group_ingress():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    group_name = str(uuid4())
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cf_client.create_stack(
        StackName=str(uuid4()),
        TemplateBody=SEC_GROUP_INGRESS.substitute(group_name=group_name),
        Parameters=[{"ParameterKey": "VPCId", "ParameterValue": vpc.id}],
        Capabilities=["CAPABILITY_NAMED_IAM"],
        OnFailure="DELETE",
    )

    groups = ec2_client.describe_security_groups()["SecurityGroups"]
    group = [g for g in groups if g["GroupName"] == group_name][0]
    group["Description"].should.equal("Test VPC security group")
    len(group["IpPermissions"]).should.be(1)
    ingress = group["IpPermissions"][0]
    ingress["FromPort"].should.equal(22)
    ingress["ToPort"].should.equal(22)
    ingress["IpProtocol"].should.equal("tcp")
    ingress["IpRanges"].should.equal(
        [{"CidrIp": "10.0.0.0/8", "Description": "Allow SSH traffic from 10.0.0.0/8"}]
    )


@mock_cloudformation
@mock_ec2
def test_security_group_ingress_without_description():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    group_name = str(uuid4())
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cf_client.create_stack(
        StackName=str(uuid4()),
        TemplateBody=SEC_GROUP_INGRESS_WITHOUT_DESC.substitute(group_name=group_name),
        Parameters=[{"ParameterKey": "VPCId", "ParameterValue": vpc.id}],
        Capabilities=["CAPABILITY_NAMED_IAM"],
        OnFailure="DELETE",
    )

    groups = ec2_client.describe_security_groups()["SecurityGroups"]
    group = [g for g in groups if g["GroupName"] == group_name][0]
    group["Description"].should.equal("Test VPC security group")
    len(group["IpPermissions"]).should.be(1)
    ingress = group["IpPermissions"][0]
    ingress["IpRanges"].should.equal([{"CidrIp": "10.0.0.0/8"}])


@mock_ec2
@mock_cloudformation
def test_stack_security_groups():

    first_desc = str(uuid4())
    second_desc = str(uuid4())
    our_template = SEC_GROUP_SOURCE.copy()
    our_template["Resources"]["my-security-group"]["Properties"][
        "GroupDescription"
    ] = second_desc
    our_template["Resources"]["InstanceSecurityGroup"]["Properties"][
        "GroupDescription"
    ] = first_desc

    template = json.dumps(our_template)

    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=template,
        Tags=[{"Key": "foo", "Value": "bar"}],
    )

    ec2 = boto3.client("ec2", region_name="us-west-1")
    instance_group = ec2.describe_security_groups(
        Filters=[{"Name": "description", "Values": [first_desc]}]
    )["SecurityGroups"][0]
    instance_group.should.have.key("Description").equal(first_desc)
    instance_group.should.have.key("Tags")
    instance_group["Tags"].should.contain({"Key": "bar", "Value": "baz"})
    instance_group["Tags"].should.contain({"Key": "foo", "Value": "bar"})
    other_group = ec2.describe_security_groups(
        Filters=[{"Name": "description", "Values": [second_desc]}]
    )["SecurityGroups"][0]

    instance = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"][
        1
    ]
    instance_id = instance["PhysicalResourceId"]

    ec2_instance = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0][
        "Instances"
    ][0]

    ec2_instance["NetworkInterfaces"][0]["Groups"][0]["GroupId"].should.equal(
        instance_group["GroupId"]
    )

    rule1, rule2 = instance_group["IpPermissions"]
    int(rule1["ToPort"]).should.equal(22)
    int(rule1["FromPort"]).should.equal(22)
    rule1["IpRanges"][0]["CidrIp"].should.equal("123.123.123.123/32")
    rule1["IpProtocol"].should.equal("tcp")

    int(rule2["ToPort"]).should.equal(8000)
    int(rule2["FromPort"]).should.equal(80)
    rule2["IpProtocol"].should.equal("tcp")
    rule2["UserIdGroupPairs"][0]["GroupId"].should.equal(other_group["GroupId"])
