from moto import mock_cloudformation_deprecated, mock_ec2_deprecated
from moto import mock_cloudformation, mock_ec2
from tests import EXAMPLE_AMI_ID
from tests.test_cloudformation.fixtures import vpc_eni
import boto
import boto.ec2
import boto.cloudformation
import boto.vpc
import boto3
import json
import sure  # noqa


@mock_ec2_deprecated
@mock_cloudformation_deprecated
def test_elastic_network_interfaces_cloudformation():
    template = vpc_eni.template
    template_json = json.dumps(template)
    conn = boto.cloudformation.connect_to_region("us-west-1")
    conn.create_stack("test_stack", template_body=template_json)
    ec2_conn = boto.ec2.connect_to_region("us-west-1")
    eni = ec2_conn.get_all_network_interfaces()[0]
    eni.private_ip_addresses.should.have.length_of(1)

    stack = conn.describe_stacks()[0]
    resources = stack.describe_resources()
    cfn_eni = [
        resource
        for resource in resources
        if resource.resource_type == "AWS::EC2::NetworkInterface"
    ][0]
    cfn_eni.physical_resource_id.should.equal(eni.id)

    outputs = {output.key: output.value for output in stack.outputs}
    outputs["ENIIpAddress"].should.equal(eni.private_ip_addresses[0].private_ip_address)


@mock_ec2
@mock_cloudformation
def test_volume_size_through_cloudformation():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    volume_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testInstance": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": EXAMPLE_AMI_ID,
                    "KeyName": "dummy",
                    "InstanceType": "t2.micro",
                    "BlockDeviceMappings": [
                        {"DeviceName": "/dev/sda2", "Ebs": {"VolumeSize": "50"}}
                    ],
                    "Tags": [
                        {"Key": "foo", "Value": "bar"},
                        {"Key": "blah", "Value": "baz"},
                    ],
                },
            }
        },
    }
    template_json = json.dumps(volume_template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    instances = ec2.describe_instances()
    volume = instances["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0][
        "Ebs"
    ]

    volumes = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])
    volumes["Volumes"][0]["Size"].should.equal(50)


@mock_ec2
@mock_cloudformation
def test_attach_internet_gateway():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    volume_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "DEVLAB1": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "internetgateway": {"Type": "AWS::EC2::InternetGateway"},
            "DEVLAB1VPGAttaching": {
                "Type": "AWS::EC2::VPCGatewayAttachment",
                "Properties": {
                    "VpcId": {"Ref": "DEVLAB1"},
                    "InternetGatewayId": {"Ref": "internetgateway"},
                },
            },
        },
    }
    template_json = json.dumps(volume_template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    stack_resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]

    # Verify VPC is created
    vpc = [r for r in stack_resources if r["ResourceType"] == "AWS::EC2::VPC"][0]
    vpc["LogicalResourceId"].should.equal("DEVLAB1")
    vpc_id = vpc["PhysicalResourceId"]

    # Verify Internet Gateway is created
    gateway_id = get_resource_id("AWS::EC2::InternetGateway", stack_resources)
    gateway = ec2.describe_internet_gateways(InternetGatewayIds=[gateway_id])[
        "InternetGateways"
    ][0]
    gateway["Attachments"].should.contain({"State": "available", "VpcId": vpc_id})
    gateway["Tags"].should.contain(
        {"Key": "aws:cloudformation:logical-id", "Value": "internetgateway"}
    )


@mock_ec2
@mock_cloudformation
def test_attach_vpn_gateway():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    vpn_gateway_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "DEVLAB1": {
                "Type": "AWS::EC2::VPC",
                "Properties": {"CidrBlock": "10.0.0.0/16"},
            },
            "DEVLAB1DCGateway": {
                "Type": "AWS::EC2::VPNGateway",
                "Properties": {"Type": "ipsec.1",},
            },
            "DEVLAB1VPGAttaching": {
                "Type": "AWS::EC2::VPCGatewayAttachment",
                "Properties": {
                    "VpcId": {"Ref": "DEVLAB1"},
                    "VpnGatewayId": {"Ref": "DEVLAB1DCGateway"},
                },
                "DependsOn": ["DEVLAB1DCGateway"],
            },
        },
    }
    template_json = json.dumps(vpn_gateway_template)
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    stack_resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]

    gateway_id = get_resource_id("AWS::EC2::VPNGateway", stack_resources)
    vpc_id = get_resource_id("AWS::EC2::VPC", stack_resources)

    gateway = ec2.describe_vpn_gateways(VpnGatewayIds=[gateway_id])["VpnGateways"][0]
    gateway["VpcAttachments"].should.contain({"State": "attached", "VpcId": vpc_id})


def get_resource_id(resource_type, stack_resources):
    r = [r for r in stack_resources if r["ResourceType"] == resource_type][0]
    return r["PhysicalResourceId"]


@mock_ec2_deprecated
@mock_cloudformation_deprecated
def test_subnet_tags_through_cloudformation():
    vpc_conn = boto.vpc.connect_to_region("us-west-1")
    vpc = vpc_conn.create_vpc("10.0.0.0/16")

    subnet_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testSubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "VpcId": vpc.id,
                    "CidrBlock": "10.0.0.0/24",
                    "AvailabilityZone": "us-west-1b",
                    "Tags": [
                        {"Key": "foo", "Value": "bar"},
                        {"Key": "blah", "Value": "baz"},
                    ],
                },
            }
        },
    }
    cf_conn = boto.cloudformation.connect_to_region("us-west-1")
    template_json = json.dumps(subnet_template)
    cf_conn.create_stack("test_stack", template_body=template_json)

    subnet = vpc_conn.get_all_subnets(filters={"cidrBlock": "10.0.0.0/24"})[0]
    subnet.tags["foo"].should.equal("bar")
    subnet.tags["blah"].should.equal("baz")
