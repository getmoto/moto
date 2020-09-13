from moto import mock_cloudformation_deprecated, mock_ec2_deprecated
from moto import mock_cloudformation, mock_ec2
from tests.test_cloudformation.fixtures import vpc_eni
import boto
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
                    "ImageId": "ami-d3adb33f",
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
