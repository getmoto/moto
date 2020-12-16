import boto3
import sure  # noqa
from moto import mock_cloudformation, mock_ec2


SEC_GROUP_INGRESS = """{
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
                "GroupName": "My-SG",
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


SEC_GROUP_INGRESS_WITHOUT_DESC = """{
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
                "GroupName": "My-SG",
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


@mock_cloudformation
@mock_ec2
def test_security_group_ingress():
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cf_client.create_stack(
        StackName="test_stack",
        TemplateBody=SEC_GROUP_INGRESS,
        Parameters=[{"ParameterKey": "VPCId", "ParameterValue": vpc.id}],
        Capabilities=["CAPABILITY_NAMED_IAM"],
        OnFailure="DELETE",
    )

    groups = ec2_client.describe_security_groups()["SecurityGroups"]
    group = [g for g in groups if g["GroupName"] == "My-SG"][0]
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

    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    cf_client.create_stack(
        StackName="test_stack",
        TemplateBody=SEC_GROUP_INGRESS_WITHOUT_DESC,
        Parameters=[{"ParameterKey": "VPCId", "ParameterValue": vpc.id}],
        Capabilities=["CAPABILITY_NAMED_IAM"],
        OnFailure="DELETE",
    )

    groups = ec2_client.describe_security_groups()["SecurityGroups"]
    group = [g for g in groups if g["GroupName"] == "My-SG"][0]
    group["Description"].should.equal("Test VPC security group")
    len(group["IpPermissions"]).should.be(1)
    ingress = group["IpPermissions"][0]
    ingress["IpRanges"].should.equal([{"CidrIp": "10.0.0.0/8"}])
