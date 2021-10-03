from botocore.exceptions import ClientError
from moto import mock_cloudformation_deprecated, mock_ec2_deprecated
from moto import mock_cloudformation, mock_ec2
from tests import EXAMPLE_AMI_ID
from tests.test_cloudformation.fixtures import ec2_classic_eip
from tests.test_cloudformation.fixtures import single_instance_with_ebs_volume
from tests.test_cloudformation.fixtures import vpc_eip
from tests.test_cloudformation.fixtures import vpc_eni
from tests.test_cloudformation.fixtures import vpc_single_instance_in_subnet
import boto
import boto.ec2
import boto.cloudformation
import boto.vpc
import boto3
import json
import pytest
import sure  # noqa


template_vpc = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "Create VPC",
    "Resources": {
        "VPC": {"Properties": {"CidrBlock": "192.168.0.0/16"}, "Type": "AWS::EC2::VPC"}
    },
}


@mock_ec2
@mock_cloudformation
def test_vpc_single_instance_in_subnet():
    template_json = json.dumps(vpc_single_instance_in_subnet.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "my_key"}],
    )

    ec2 = boto3.client("ec2", region_name="us-west-1")

    vpc = ec2.describe_vpcs(Filters=[{"Name": "cidrBlock", "Values": ["10.0.0.0/16"]}])[
        "Vpcs"
    ][0]
    vpc["CidrBlock"].should.equal("10.0.0.0/16")

    ec2.describe_internet_gateways()["InternetGateways"].should.have.length_of(1)

    subnet = ec2.describe_subnets(
        Filters=[{"Name": "vpcId", "Values": [vpc["VpcId"]]}]
    )["Subnets"][0]
    subnet["VpcId"].should.equal(vpc["VpcId"])

    ec2 = boto3.client("ec2", region_name="us-west-1")
    reservation = ec2.describe_instances()["Reservations"][0]
    instance = reservation["Instances"][0]
    instance["Tags"].should.contain({"Key": "Foo", "Value": "Bar"})
    # Check that the EIP is attached the the EC2 instance
    eip = ec2.describe_addresses()["Addresses"][0]
    eip["Domain"].should.equal("vpc")
    eip["InstanceId"].should.equal(instance["InstanceId"])

    security_group = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc["VpcId"]]}]
    )["SecurityGroups"][0]
    security_group["VpcId"].should.equal(vpc["VpcId"])

    stack = cf.describe_stacks(StackName="test_stack")["Stacks"][0]

    vpc["Tags"].should.contain({"Key": "Application", "Value": stack["StackId"]})

    resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    vpc_resource = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::VPC"
    ][0]
    vpc_resource["PhysicalResourceId"].should.equal(vpc["VpcId"])

    subnet_resource = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::Subnet"
    ][0]
    subnet_resource["PhysicalResourceId"].should.equal(subnet["SubnetId"])

    eip_resource = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::EIP"
    ][0]
    eip_resource["PhysicalResourceId"].should.equal(eip["PublicIp"])


@mock_cloudformation
@mock_ec2
def test_delete_stack_with_resource_missing_delete_attr():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    name = "test_stack"

    cf.create_stack(StackName=name, TemplateBody=json.dumps(template_vpc))
    cf.describe_stacks(StackName=name)["Stacks"].should.have.length_of(1)
    ec2.describe_vpcs()["Vpcs"].should.have.length_of(2)

    cf.delete_stack(
        StackName=name
    )  # should succeed, despite the fact that the resource itself cannot be deleted
    with pytest.raises(ClientError) as exc:
        cf.describe_stacks(StackName=name)
    err = exc.value.response["Error"]
    err.should.have.key("Code").equals("ValidationError")
    err.should.have.key("Message").equals("Stack with id test_stack does not exist")

    # We still have two VPCs, as the VPC-object does not have a delete-method yet
    ec2.describe_vpcs()["Vpcs"].should.have.length_of(2)


# Has boto3 equivalent
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
def test_elastic_network_interfaces_cloudformation_boto3():
    template = vpc_eni.template
    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    eni = ec2.describe_network_interfaces()["NetworkInterfaces"][0]
    eni["PrivateIpAddresses"].should.have.length_of(1)
    private_ip_address = eni["PrivateIpAddresses"][0]["PrivateIpAddress"]

    resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    cfn_eni = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::NetworkInterface"
    ][0]
    cfn_eni["PhysicalResourceId"].should.equal(eni["NetworkInterfaceId"])

    outputs = cf.describe_stacks(StackName="test_stack")["Stacks"][0]["Outputs"]
    outputs.should.contain(
        {"OutputKey": "ENIIpAddress", "OutputValue": private_ip_address}
    )


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

    resource = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ][0]
    resource.should.have.key("LogicalResourceId").being.equal("testInstance")
    resource.should.have.key("PhysicalResourceId").shouldnt.be.none
    resource.should.have.key("ResourceType").being.equal("AWS::EC2::Instance")

    instances = ec2.describe_instances(InstanceIds=[resource["PhysicalResourceId"]])
    volume = instances["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0][
        "Ebs"
    ]

    volumes = ec2.describe_volumes(VolumeIds=[volume["VolumeId"]])
    volumes["Volumes"][0]["Size"].should.equal(50)


# Has boto3 equivalent
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


@mock_ec2
@mock_cloudformation
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    subnet = ec2.describe_subnets(
        Filters=[{"Name": "cidrBlock", "Values": ["10.0.0.0/24"]}]
    )["Subnets"][0]
    subnet["Tags"].should.contain({"Key": "foo", "Value": "bar"})
    subnet["Tags"].should.contain({"Key": "blah", "Value": "baz"})


@mock_ec2
@mock_cloudformation
def test_single_instance_with_ebs_volume():
    template_json = json.dumps(single_instance_with_ebs_volume.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(
        StackName="test_stack",
        TemplateBody=template_json,
        Parameters=[{"ParameterKey": "KeyName", "ParameterValue": "key_name"}],
    )

    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2_instance = ec2.describe_instances()["Reservations"][0]["Instances"][0]

    volumes = ec2.describe_volumes()["Volumes"]
    # Grab the mounted drive
    volume = [
        volume for volume in volumes if volume["Attachments"][0]["Device"] == "/dev/sdh"
    ][0]
    volume["State"].should.equal("in-use")
    volume["Attachments"][0]["InstanceId"].should.equal(ec2_instance["InstanceId"])

    resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    ebs_volumes = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::Volume"
    ]
    ebs_volumes[0]["PhysicalResourceId"].should.equal(volume["VolumeId"])


@mock_ec2
@mock_cloudformation
def test_classic_eip():
    template_json = json.dumps(ec2_classic_eip.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    eip = ec2.describe_addresses()["Addresses"][0]

    resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    cfn_eip = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::EIP"
    ][0]
    cfn_eip["PhysicalResourceId"].should.equal(eip["PublicIp"])


@mock_ec2
@mock_cloudformation
def test_vpc_eip():
    template_json = json.dumps(vpc_eip.template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")
    eip = ec2.describe_addresses()["Addresses"][0]

    resources = cf.list_stack_resources(StackName="test_stack")[
        "StackResourceSummaries"
    ]
    cfn_eip = [
        resource
        for resource in resources
        if resource["ResourceType"] == "AWS::EC2::EIP"
    ][0]
    cfn_eip["PhysicalResourceId"].should.equal(eip["PublicIp"])


@mock_cloudformation
@mock_ec2
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    ec2 = boto3.client("ec2", region_name="us-west-1")
    vpc = ec2.describe_vpcs(Filters=[{"Name": "cidrBlock", "Values": ["10.0.0.0/16"]}])[
        "Vpcs"
    ][0]

    igws = ec2.describe_internet_gateways(
        Filters=[{"Name": "attachment.vpc-id", "Values": [vpc["VpcId"]]}]
    )["InternetGateways"]
    igws.should.have.length_of(1)


@mock_cloudformation
@mock_ec2
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)

    peering_connections = ec2_client.describe_vpc_peering_connections()[
        "VpcPeeringConnections"
    ]
    peering_connections.should.have.length_of(1)


@mock_cloudformation
@mock_ec2
def test_multiple_security_group_ingress_separate_from_security_group_by_id():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group1": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [{"Key": "sg-name", "Value": "sg1"}],
                },
            },
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [{"Key": "sg-name", "Value": "sg2"}],
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    ec2 = boto3.client("ec2", region_name="us-west-1")

    security_group1 = get_secgroup_by_tag(ec2, "sg1")
    security_group2 = get_secgroup_by_tag(ec2, "sg2")

    security_group1["IpPermissions"].should.have.length_of(1)
    security_group1["IpPermissions"][0]["UserIdGroupPairs"].should.have.length_of(1)
    security_group1["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"].should.equal(
        security_group2["GroupId"]
    )
    security_group1["IpPermissions"][0]["IpProtocol"].should.equal("tcp")
    security_group1["IpPermissions"][0]["FromPort"].should.equal(80)
    security_group1["IpPermissions"][0]["ToPort"].should.equal(8080)


@mock_cloudformation
@mock_ec2
def test_security_group_ingress_separate_from_security_group_by_id():
    ec2 = boto3.client("ec2", region_name="us-west-1")
    ec2.create_security_group(
        GroupName="test-security-group1", Description="test security group"
    )

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group2": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "Tags": [{"Key": "sg-name", "Value": "sg2"}],
                },
            },
            "test-sg-ingress": {
                "Type": "AWS::EC2::SecurityGroupIngress",
                "Properties": {
                    "GroupName": "test-security-group1",
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    security_group1 = ec2.describe_security_groups(GroupNames=["test-security-group1"])[
        "SecurityGroups"
    ][0]
    security_group2 = get_secgroup_by_tag(ec2, "sg2")

    security_group1["IpPermissions"].should.have.length_of(1)
    security_group1["IpPermissions"][0]["UserIdGroupPairs"].should.have.length_of(1)
    security_group1["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"].should.equal(
        security_group2["GroupId"]
    )
    security_group1["IpPermissions"][0]["IpProtocol"].should.equal("tcp")
    security_group1["IpPermissions"][0]["FromPort"].should.equal(80)
    security_group1["IpPermissions"][0]["ToPort"].should.equal(8080)


@mock_cloudformation
@mock_ec2
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    security_group1 = get_secgroup_by_tag(ec2_client, "sg1")
    security_group2 = get_secgroup_by_tag(ec2_client, "sg2")

    security_group1["IpPermissions"].should.have.length_of(1)
    security_group1["IpPermissions"][0]["UserIdGroupPairs"].should.have.length_of(1)
    security_group1["IpPermissions"][0]["UserIdGroupPairs"][0]["GroupId"].should.equal(
        security_group2["GroupId"]
    )
    security_group1["IpPermissions"][0]["IpProtocol"].should.equal("tcp")
    security_group1["IpPermissions"][0]["FromPort"].should.equal(80)
    security_group1["IpPermissions"][0]["ToPort"].should.equal(8080)


@mock_cloudformation
@mock_ec2
def test_security_group_with_update():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    ec2_client = boto3.client("ec2", region_name="us-west-1")
    vpc1 = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc2 = ec2.create_vpc(CidrBlock="10.1.0.0/16")

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "test-security-group": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "test security group",
                    "VpcId": vpc1.id,
                    "Tags": [{"Key": "sg-name", "Value": "sg"}],
                },
            }
        },
    }

    template_json = json.dumps(template)
    cf = boto3.client("cloudformation", region_name="us-west-1")
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    security_group = get_secgroup_by_tag(ec2_client, "sg")
    security_group["VpcId"].should.equal(vpc1.id)

    template["Resources"]["test-security-group"]["Properties"]["VpcId"] = vpc2.id
    template_json = json.dumps(template)
    cf.update_stack(StackName="test_stack", TemplateBody=template_json)
    security_group = get_secgroup_by_tag(ec2_client, "sg")
    security_group["VpcId"].should.equal(vpc2.id)


@mock_cloudformation
@mock_ec2
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
    cf.create_stack(StackName="test_stack", TemplateBody=template_json)
    subnet = ec2_client.describe_subnets(
        Filters=[{"Name": "cidrBlock", "Values": ["10.0.0.0/24"]}]
    )["Subnets"][0]
    subnet["AvailabilityZone"].should.equal("us-west-1b")


def get_secgroup_by_tag(ec2, sg_):
    return ec2.describe_security_groups(
        Filters=[{"Name": "tag:sg-name", "Values": [sg_]}]
    )["SecurityGroups"][0]
