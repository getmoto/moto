import json
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import EXAMPLE_AMI_ID
from tests.test_cloudformation.fixtures import (
    ec2_classic_eip,
    single_instance_with_ebs_volume,
    vpc_eip,
    vpc_eni,
    vpc_single_instance_in_subnet,
)

template_vpc = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Create VPC",
    "Resources": {
        "VPC": {"Properties": {"CidrBlock": "192.168.0.0/16"}, "Type": "AWS::EC2::VPC"}
    },
}

template_subnet = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Create VPC",
    "Resources": {
        "VPC": {"Properties": {"CidrBlock": "192.168.0.0/16"}, "Type": "AWS::EC2::VPC"},
        "Subnet": {
            "Properties": {"VpcId": {"Ref": "VPC"}, "CidrBlock": "192.168.0.0/18"},
            "Type": "AWS::EC2::Subnet",
        },
    },
}


@mock_aws
def test_vpc_single_instance_in_subnet():
    template_json = json.dumps(vpc_single_instance_in_subnet.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "my_key"}],
    )

    ec2 = boto3.client("ec2", region_name="us-west-1")

    stack = cf.describe_stacks(StackName=stack_name)["Stacks"][0]

    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    vpc_id = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::VPC"
    ][0]["PhysicalResourceId"]

    vpc = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"][0]
    assert vpc["CidrBlock"] == "10.0.0.0/16"
    assert {"Key": "Application", "Value": stack["StackId"]} in vpc["Tags"]

    security_group = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc["VpcId"]]}]
    )["SecurityGroups"][0]
    assert security_group["VpcId"] == vpc["VpcId"]

    subnet_id = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::Subnet"
    ][0]["PhysicalResourceId"]

    subnet = ec2.describe_subnets(SubnetIds=[subnet_id])["Subnets"][0]
    assert subnet["VpcId"] == vpc["VpcId"]

    instance_id = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::Instance"
    ][0]["PhysicalResourceId"]
    res = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0]
    instance = res["Instances"][0]
    assert {"Key": "Foo", "Value": "Bar"} in instance["Tags"]

    eip_id = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::EIP"
    ][0]["PhysicalResourceId"]
    eip = ec2.describe_addresses(PublicIps=[eip_id])["Addresses"][0]
    assert eip["Domain"] == "vpc"
    assert eip["InstanceId"] == instance["InstanceId"]


@mock_aws
def test_delete_stack_with_vpc():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    name = str(uuid4())[0:6]

    cf.create_stack(StackName=name, TemplateBody=json.dumps(template_vpc))
    resources = cf.list_stack_resources(StackName=name)["StackResourceSummaries"]
    vpc_id = resources[0]["PhysicalResourceId"]

    assert len(ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"]) == 1

    cf.delete_stack(StackName=name)
    with pytest.raises(ec2.exceptions.ClientError):
        ec2.describe_vpcs(VpcIds=[vpc_id])


@mock_aws
def test_delete_stack_with_subnet():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    name = str(uuid4())[0:6]

    cf.create_stack(StackName=name, TemplateBody=json.dumps(template_subnet))
    subnet_ids = [
        resource["PhysicalResourceId"]
        for resource in cf.list_stack_resources(StackName=name)[
            "StackResourceSummaries"
        ]
        if resource["ResourceType"] == "AWS::EC2::Subnet"
    ]

    assert len(ec2.describe_subnets(SubnetIds=subnet_ids)["Subnets"]) == 1

    cf.delete_stack(StackName=name)
    with pytest.raises(ec2.exceptions.ClientError):
        ec2.describe_subnets(SubnetIds=subnet_ids)


@mock_aws
def test_elastic_network_interfaces_cloudformation_boto3():
    template = vpc_eni.template
    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    all_enis = ec2.describe_network_interfaces()["NetworkInterfaces"]
    all_eni_ids = [eni["NetworkInterfaceId"] for eni in all_enis]
    all_ips = [eni["PrivateIpAddresses"][0]["PrivateIpAddress"] for eni in all_enis]

    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    cfn_eni = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::NetworkInterface"
    ][0]
    assert cfn_eni["PhysicalResourceId"] in all_eni_ids

    outputs = cf.describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    received_ip = [
        o["OutputValue"] for o in outputs if o["OutputKey"] == "ENIIpAddress"
    ][0]
    assert received_ip in all_ips


@mock_aws
def test_volume_size_through_cloudformation():
    ec2 = boto3.client("ec2", region_name="us-east-1")
    cf = boto3.client("cloudformation", region_name="us-east-1")

    tag_value = str(uuid4())
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
                        {"Key": "blah", "Value": tag_value},
                    ],
                },
            }
        },
    }
    template_json = json.dumps(volume_template)

    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    resource = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"][
        0
    ]
    assert resource["LogicalResourceId"] == "testInstance"
    assert resource["PhysicalResourceId"] is not None
    assert resource["ResourceType"] == "AWS::EC2::Instance"

    instances = ec2.describe_instances(InstanceIds=[resource["PhysicalResourceId"]])

    volume = instances["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0][
        "Ebs"
    ]

    volumes = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])
    assert volumes["Volumes"][0]["Size"] == 50


@mock_aws
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
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    stack_resources = cf.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    # Verify VPC is created
    vpc = [r for r in stack_resources if r["ResourceType"] == "AWS::EC2::VPC"][0]
    assert vpc["LogicalResourceId"] == "DEVLAB1"
    vpc_id = vpc["PhysicalResourceId"]

    # Verify Internet Gateway is created
    gateway_id = get_resource_id("AWS::EC2::InternetGateway", stack_resources)
    gateway = ec2.describe_internet_gateways(InternetGatewayIds=[gateway_id])[
        "InternetGateways"
    ][0]
    assert {"State": "available", "VpcId": vpc_id} in gateway["Attachments"]
    assert {
        "Key": "aws:cloudformation:logical-id",
        "Value": "internetgateway",
    } in gateway["Tags"]


@mock_aws
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
                "Properties": {"Type": "ipsec.1"},
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
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    stack_resources = cf.list_stack_resources(StackName=stack_name)[
        "StackResourceSummaries"
    ]

    gateway_id = get_resource_id("AWS::EC2::VPNGateway", stack_resources)
    vpc_id = get_resource_id("AWS::EC2::VPC", stack_resources)

    gateway = ec2.describe_vpn_gateways(VpnGatewayIds=[gateway_id])["VpnGateways"][0]
    assert {"State": "attached", "VpcId": vpc_id} in gateway["VpcAttachments"]


def get_resource_id(resource_type, stack_resources):
    r = [r for r in stack_resources if r["ResourceType"] == resource_type][0]
    return r["PhysicalResourceId"]


@mock_aws
def test_subnet_tags_through_cloudformation_boto3():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2_res = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2_res.create_vpc(CidrBlock="10.0.0.0/16")

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
    template_json = json.dumps(subnet_template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    subnet_id = resources[0]["PhysicalResourceId"]

    subnet = ec2.describe_subnets(SubnetIds=[subnet_id])["Subnets"][0]
    assert subnet["CidrBlock"] == "10.0.0.0/24"
    assert {"Key": "foo", "Value": "bar"} in subnet["Tags"]
    assert {"Key": "blah", "Value": "baz"} in subnet["Tags"]


@mock_aws
def test_single_instance_with_ebs_volume():
    template_json = json.dumps(single_instance_with_ebs_volume.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "key_name"}],
    )
    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    instance_id = [
        r["PhysicalResourceId"]
        for r in resources
        if r["ResourceType"] == "AWS::EC2::Instance"
    ][0]
    volume_id = [
        r["PhysicalResourceId"]
        for r in resources
        if r["ResourceType"] == "AWS::EC2::Volume"
    ][0]

    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2_instance = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"][0][
        "Instances"
    ][0]

    volumes = ec2.describe_volumes(VolumeIds=[volume_id])["Volumes"]
    # Grab the mounted drive
    volume = [
        volume for volume in volumes if volume["Attachments"][0]["Device"] == "/dev/sdh"
    ][0]
    assert volume["State"] == "in-use"
    assert volume["Attachments"][0]["InstanceId"] == ec2_instance["InstanceId"]


@mock_aws
def test_classic_eip():
    template_json = json.dumps(ec2_classic_eip.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    all_ips = [eip["PublicIp"] for eip in ec2.describe_addresses()["Addresses"]]

    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    cfn_eip = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::EIP"
    ][0]
    assert cfn_eip["PhysicalResourceId"] in all_ips


@mock_aws
def test_vpc_eip():
    template_json = json.dumps(vpc_eip.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    ec2 = boto3.client("ec2", region_name="us-west-1")
    all_ips = [eip["PublicIp"] for eip in ec2.describe_addresses()["Addresses"]]

    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    cfn_eip = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::EIP"
    ][0]
    assert cfn_eip["PhysicalResourceId"] in all_ips


@mock_aws
def test_vpc_gateway_attachment_creation_should_attach_itself_to_vpc():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "internetgateway": {"Type": "AWS::EC2::InternetGateway"},
            "testvpc": {
                "Type": "AWS::EC2::VPC",
                "Properties": {
                    "CidrBlock": "10.0.0.0/16",
                    "EnableDnsHostnames": "true",
                    "EnableDnsSupport": "true",
                    "InstanceTenancy": "default",
                },
            },
            "vpcgatewayattachment": {
                "Type": "AWS::EC2::VPCGatewayAttachment",
                "Properties": {
                    "InternetGatewayId": {"Ref": "internetgateway"},
                    "VpcId": {"Ref": "testvpc"},
                },
            },
        },
    }

    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    vpc_id = resources[1]["PhysicalResourceId"]

    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.describe_vpcs(VpcIds=[vpc_id])["Vpcs"][0]
    assert vpc["CidrBlock"] == "10.0.0.0/16"

    igws = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc["VpcId"]]}]
    )["InternetGateways"]
    assert len(igws) == 1


@mock_aws
def test_vpc_peering_creation():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    vpc_source = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    peer_vpc = ec2.create_vpc(CidrBlock="10.1.0.0/16")
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "vpcpeeringconnection": {
                "Type": "AWS::EC2::VPCPeeringConnection",
                "Properties": {"PeerVpcId": peer_vpc.id, "VpcId": vpc_source.id},
            }
        },
    }

    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    our_vpx_id = resources[0]["PhysicalResourceId"]

    peering_connections = ec2_client.describe_vpc_peering_connections(
        VpcPeeringConnectionIds=[our_vpx_id]
    )["VpcPeeringConnections"]
    assert len(peering_connections) == 1


@mock_aws
def test_multiple_security_group_ingress_separate_from_security_group_by_id():
    sg1 = str(uuid4())[0:6]
    sg2 = str(uuid4())[0:6]
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group1": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [{"Key": "sg-name", "Value": sg1}],
                },
            },
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [{"Key": "sg-name", "Value": sg2}],
                },
            },
            "test-sg-ingress": {
                "Type": "AWS::EC2::SecurityGroupIngress",
                "Properties": {
                    "GroupId": {"Ref": "test-security-group1"},
                    "IpProtocol": "tcp",
                    "FromPort": "80",
                    "ToPort": "8080",
                    "SourceSecurityGroupId": {"Ref": "test-security-group2"},
                },
            },
        },
    }

    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName=str(uuid4())[0:6], TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")

    security_group1 = get_secgroup_by_tag(ec2, sg1)
    security_group2 = get_secgroup_by_tag(ec2, sg2)

    assert len(security_group1["IpPermissions"]) == 1
    assert len(security_group1["IpPermissions"][0]["UserIdGroupPairs"]) == 1
    assert (
        security_group1["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"]
        == security_group2["GroupId"]
    )
    assert security_group1["IpPermissions"][0]["IpProtocol"] == "tcp"
    assert security_group1["IpPermissions"][0]["FromPort"] == 80
    assert security_group1["IpPermissions"][0]["ToPort"] == 8080


@mock_aws
def test_security_group_ingress_separate_from_security_group_by_id():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    sg_name = str(uuid4())
    ec2.create_security_group(GroupName=sg_name, Description="test security group")

    sg_2 = str(uuid4())[0:6]
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [{"Key": "sg-name", "Value": sg_2}],
                },
            },
            "test-sg-ingress": {
                "Type": "AWS::EC2::SecurityGroupIngress",
                "Properties": {
                    "GroupName": sg_name,
                    "IpProtocol": "tcp",
                    "FromPort": "80",
                    "ToPort": "8080",
                    "SourceSecurityGroupId": {"Ref": "test-security-group2"},
                },
            },
        },
    }

    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName=str(uuid4())[0:6], TemplateBody=template_json)
    security_group1 = ec2.describe_security_groups(GroupNames=[sg_name])[
        "SecurityGroups"
    ][0]
    security_group2 = get_secgroup_by_tag(ec2, sg_2)

    assert len(security_group1["IpPermissions"]) == 1
    assert len(security_group1["IpPermissions"][0]["UserIdGroupPairs"]) == 1
    assert (
        security_group1["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"]
        == security_group2["GroupId"]
    )
    assert security_group1["IpPermissions"][0]["IpProtocol"] == "tcp"
    assert security_group1["IpPermissions"][0]["FromPort"] == 80
    assert security_group1["IpPermissions"][0]["ToPort"] == 8080


@mock_aws
def test_security_group_ingress_separate_from_security_group_by_id_using_vpc():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group1": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "VpcId": vpc.id,
                    "Tags": [{"Key": "sg-name", "Value": "sg1"}],
                },
            },
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "VpcId": vpc.id,
                    "Tags": [{"Key": "sg-name", "Value": "sg2"}],
                },
            },
            "test-sg-ingress": {
                "Type": "AWS::EC2::SecurityGroupIngress",
                "Properties": {
                    "GroupId": {"Ref": "test-security-group1"},
                    "VpcId": vpc.id,
                    "IpProtocol": "tcp",
                    "FromPort": "80",
                    "ToPort": "8080",
                    "SourceSecurityGroupId": {"Ref": "test-security-group2"},
                },
            },
        },
    }

    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName=str(uuid4())[0:6], TemplateBody=template_json)
    security_group1 = get_secgroup_by_tag(ec2_client, "sg1")
    security_group2 = get_secgroup_by_tag(ec2_client, "sg2")

    assert len(security_group1["IpPermissions"]) == 1
    assert len(security_group1["IpPermissions"][0]["UserIdGroupPairs"]) == 1
    assert (
        security_group1["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"]
        == security_group2["GroupId"]
    )
    assert security_group1["IpPermissions"][0]["IpProtocol"] == "tcp"
    assert security_group1["IpPermissions"][0]["FromPort"] == 80
    assert security_group1["IpPermissions"][0]["ToPort"] == 8080


@mock_aws
def test_security_group_with_update():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.1.0.0/16")

    sg = str(uuid4())[0:6]
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "VpcId": vpc1.id,
                    "Tags": [{"Key": "sg-name", "Value": sg}],
                },
            }
        },
    }

    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    security_group = get_secgroup_by_tag(ec2_client, sg)
    assert security_group["VpcId"] == vpc1.id

    template["Resources"]["test-security-group"]["Properties"]["VpcId"] = vpc2.id
    template_json = json.dumps(template)
    cf.update_stack(StackName=stack_name, TemplateBody=template_json)
    security_group = get_secgroup_by_tag(ec2_client, sg)
    assert security_group["VpcId"] == vpc2.id


@mock_aws
def test_subnets_should_be_created_with_availability_zone():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")

    subnet_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "testSubnet": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "VpcId": vpc.id,
                    "CidrBlock": "10.0.0.0/24",
                    "AvailabilityZone": "us-west-1b",
                },
            }
        },
    }
    cf = boto3.client("cloudformation", region_name="us-west-1")
    template_json = json.dumps(subnet_template)
    stack_name = str(uuid4())[0:6]
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)
    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    subnet_id = resources[0]["PhysicalResourceId"]
    subnet = ec2_client.describe_subnets(SubnetIds=[subnet_id])["Subnets"][0]
    assert subnet["CidrBlock"] == "10.0.0.0/24"
    assert subnet["AvailabilityZone"] == "us-west-1b"


def get_secgroup_by_tag(ec2, sg_):
    return ec2.describe_security_groups(
        Filters=[{"Name": "tag:sg-name", "Values": [sg_]}]
    )["SecurityGroups"][0]


@mock_aws
def test_vpc_endpoint_creation():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="10.0.0.0/24", AvailabilityZone="us-west-1a"
    )

    subnet_template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Parameters": {
            "EndpointSubnetId": {"Type": "String"},
            "EndpointVpcId": {"Type": "String"},
            "EndpointServiceName": {"Type": "String"},
        },
        "Resources": {
            "GwlbVpcEndpoint": {
                "Type": "AWS::EC2::VPCEndpoint",
                "Properties": {
                    "ServiceName": {"Ref": "EndpointServiceName"},
                    "SubnetIds": [{"Ref": "EndpointSubnetId"}],
                    "VpcEndpointType": "GatewayLoadBalancer",
                    "VpcId": {"Ref": "EndpointVpcId"},
                },
            }
        },
        "Outputs": {
            "EndpointId": {
                "Description": "Id of the endpoint created",
                "Value": {"Ref": "GwlbVpcEndpoint"},
            },
        },
    }
    cf = boto3.client("cloudformation", region_name="us-west-1")
    template_json = json.dumps(subnet_template)
    stack_name = str(uuid4())[0:6]
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=template_json,
        Parameters=[
            {"ParameterKey": "EndpointSubnetId", "ParameterValue": subnet1.id},
            {"ParameterKey": "EndpointVpcId", "ParameterValue": vpc.id},
            {"ParameterKey": "EndpointServiceName", "ParameterValue": "serv_name"},
        ],
    )
    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    assert len(resources) == 1
    assert resources[0]["LogicalResourceId"] == "GwlbVpcEndpoint"
    vpc_endpoint_id = resources[0]["PhysicalResourceId"]

    outputs = cf.describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    assert len(outputs) == 1
    assert outputs[0] == {
        "OutputKey": "EndpointId",
        "OutputValue": vpc_endpoint_id,
        "Description": "Id of the endpoint created",
    }

    endpoint = ec2_client.describe_vpc_endpoints(VpcEndpointIds=[vpc_endpoint_id])[
        "VpcEndpoints"
    ][0]
    assert endpoint["VpcId"] == vpc.id
    assert endpoint["ServiceName"] == "serv_name"
    assert endpoint["State"] == "available"
    assert endpoint["SubnetIds"] == [subnet1.id]
    assert endpoint["VpcEndpointType"] == "GatewayLoadBalancer"


@mock_aws
def test_launch_template_create():
    cf = boto3.client("cloudformation", region_name="us-west-1")
    ec2 = boto3.client("ec2", region_name="us-west-1")

    launch_template_name = str(uuid4())[0:6]
    logical_id = str(uuid4())[0:6]
    stack_name = str(uuid4())[0:6]

    lt_tags = [{"Key": "lt-tag-key", "Value": "lt-tag-value"}]

    template_json = json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                logical_id: {
                    "Type": "AWS::EC2::LaunchTemplate",
                    "Properties": {
                        "LaunchTemplateName": launch_template_name,
                        "VersionDescription": "some template",
                        "LaunchTemplateData": {
                            "TagSpecifications": [
                                {
                                    "ResourceType": "instance",
                                    "Tags": [
                                        {"Key": "i-tag-key", "Value": "i-tag-value"}
                                    ],
                                }
                            ]
                        },
                        "TagSpecifications": [
                            {
                                "ResourceType": "launch-template",
                                "Tags": lt_tags,
                            }
                        ],
                    },
                }
            },
            "Outputs": {
                "LaunchTemplateId": {
                    "Description": "The ID of the created launch template",
                    "Value": {"Ref": logical_id},
                },
            },
        }
    )

    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    assert len(resources) == 1
    assert resources[0]["LogicalResourceId"] == logical_id
    launch_template_id = resources[0]["PhysicalResourceId"]

    outputs = cf.describe_stacks(StackName=stack_name)["Stacks"][0]["Outputs"]
    assert len(outputs) == 1
    assert outputs[0] == {
        "OutputKey": "LaunchTemplateId",
        "OutputValue": launch_template_id,
        "Description": "The ID of the created launch template",
    }

    launch_template = ec2.describe_launch_templates(
        LaunchTemplateNames=[launch_template_name]
    )["LaunchTemplates"][0]
    assert launch_template["LaunchTemplateName"] == launch_template_name
    assert launch_template["LaunchTemplateId"] == launch_template_id
    assert launch_template["Tags"] == lt_tags

    launch_template_version = ec2.describe_launch_template_versions(
        LaunchTemplateName=launch_template_name
    )["LaunchTemplateVersions"][0]
    assert launch_template_version["LaunchTemplateName"] == launch_template_name
    assert launch_template_version["LaunchTemplateId"] == launch_template_id
    assert (
        launch_template_version["LaunchTemplateData"]["TagSpecifications"][0][
            "ResourceType"
        ]
        == "instance"
    )


@mock_aws
def test_launch_template_update():
    cf = boto3.client("cloudformation", region_name="us-west-1")
    ec2 = boto3.client("ec2", region_name="us-west-1")

    launch_template_name = str(uuid4())[0:6]
    logical_id = str(uuid4())[0:6]
    stack_name = str(uuid4())[0:6]

    template_json = json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                logical_id: {
                    "Type": "AWS::EC2::LaunchTemplate",
                    "Properties": {
                        "LaunchTemplateName": launch_template_name,
                        "VersionDescription": "some template",
                        "LaunchTemplateData": {"UserData": ""},
                    },
                }
            },
        }
    )

    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    template_json = json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                logical_id: {
                    "Type": "AWS::EC2::LaunchTemplate",
                    "Properties": {
                        "LaunchTemplateName": launch_template_name,
                        "VersionDescription": "a better template",
                        "LaunchTemplateData": {"UserData": ""},
                    },
                }
            },
        }
    )

    cf.update_stack(StackName=stack_name, TemplateBody=template_json)

    resources = cf.list_stack_resources(StackName=stack_name)["StackResourceSummaries"]
    assert len(resources) == 1

    launch_template_versions = ec2.describe_launch_template_versions(
        LaunchTemplateName=launch_template_name
    )["LaunchTemplateVersions"]
    assert len(launch_template_versions) == 2
    assert launch_template_versions[0]["VersionDescription"] == "some template"
    assert launch_template_versions[1]["VersionDescription"] == "a better template"


@mock_aws
def test_launch_template_delete():
    cf = boto3.client("cloudformation", region_name="us-west-1")
    ec2 = boto3.client("ec2", region_name="us-west-1")

    launch_template_name = str(uuid4())[0:6]
    logical_id = str(uuid4())[0:6]
    stack_name = str(uuid4())[0:6]

    template_json = json.dumps(
        {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                logical_id: {
                    "Type": "AWS::EC2::LaunchTemplate",
                    "Properties": {
                        "LaunchTemplateName": launch_template_name,
                        "VersionDescription": "some template",
                        "LaunchTemplateData": {"UserData": ""},
                    },
                }
            },
        }
    )
    cf.create_stack(StackName=stack_name, TemplateBody=template_json)

    cf.delete_stack(StackName=stack_name)

    with pytest.raises(ClientError) as exc:
        ec2.describe_launch_templates(LaunchTemplateNames=[launch_template_name])
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidLaunchTemplateName.NotFoundException"
    assert (
        err["Message"]
        == "At least one of the launch templates specified in the request does not exist."
    )
