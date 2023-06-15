import base64
import boto3
import os
import pytest

from botocore.exceptions import ClientError
from moto import mock_autoscaling, mock_ec2, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID
from unittest import mock, SkipTest


@mock_autoscaling
def test_create_launch_configuration():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t1.micro",
        KeyName="the_keys",
        SecurityGroups=["default", "default2"],
        UserData="This is some user_data",
        InstanceMonitoring={"Enabled": True},
        IamInstanceProfile=f"arn:aws:iam::{ACCOUNT_ID}:instance-profile/testing",
        SpotPrice="0.1",
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    assert launch_config["LaunchConfigurationName"] == "tester"
    assert "LaunchConfigurationARN" in launch_config
    assert launch_config["ImageId"] == EXAMPLE_AMI_ID
    assert launch_config["InstanceType"] == "t1.micro"
    assert launch_config["KeyName"] == "the_keys"
    assert set(launch_config["SecurityGroups"]) == set(["default", "default2"])
    userdata = launch_config["UserData"]
    userdata = base64.b64decode(userdata)
    assert userdata == b"This is some user_data"
    assert launch_config["InstanceMonitoring"] == {"Enabled": True}
    assert (
        launch_config["IamInstanceProfile"]
        == f"arn:aws:iam::{ACCOUNT_ID}:instance-profile/testing"
    )
    assert launch_config["SpotPrice"] == "0.1"
    assert launch_config["BlockDeviceMappings"] == []


@mock_autoscaling
def test_create_launch_configuration_with_block_device_mappings():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t1.micro",
        KeyName="the_keys",
        SecurityGroups=["default", "default2"],
        UserData="This is some user_data",
        InstanceMonitoring={"Enabled": True},
        IamInstanceProfile=f"arn:aws:iam::{ACCOUNT_ID}:instance-profile/testing",
        SpotPrice="0.1",
        BlockDeviceMappings=[
            {"DeviceName": "/dev/xvdb", "VirtualName": "ephemeral0"},
            {
                "DeviceName": "/dev/xvdp",
                "Ebs": {"SnapshotId": "snap-1234abcd", "VolumeType": "standard"},
            },
            {
                "DeviceName": "/dev/xvdh",
                "Ebs": {
                    "VolumeType": "io1",
                    "VolumeSize": 100,
                    "Iops": 1000,
                    "DeleteOnTermination": False,
                },
            },
        ],
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    assert launch_config["LaunchConfigurationName"] == "tester"

    mappings = launch_config["BlockDeviceMappings"]
    assert len(mappings) == 3

    xvdh = [m for m in mappings if m["DeviceName"] == "/dev/xvdh"][0]
    xvdp = [m for m in mappings if m["DeviceName"] == "/dev/xvdp"][0]
    xvdb = [m for m in mappings if m["DeviceName"] == "/dev/xvdb"][0]

    assert "VirtualName" not in xvdh
    assert "Ebs" in xvdh
    assert xvdh["Ebs"]["VolumeSize"] == 100
    assert xvdh["Ebs"]["VolumeType"] == "io1"
    assert xvdh["Ebs"]["DeleteOnTermination"] is False
    assert xvdh["Ebs"]["Iops"] == 1000

    assert "VirtualName" not in xvdp
    assert "Ebs" in xvdp
    assert xvdp["Ebs"]["SnapshotId"] == "snap-1234abcd"
    assert xvdp["Ebs"]["VolumeType"] == "standard"

    assert xvdb["VirtualName"] == "ephemeral0"
    assert "Ebs" not in xvdb


@mock_autoscaling
def test_create_launch_configuration_additional_parameters():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        ClassicLinkVPCId="vpc_id",
        ClassicLinkVPCSecurityGroups=["classic_sg1"],
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t1.micro",
        EbsOptimized=True,
        AssociatePublicIpAddress=True,
        MetadataOptions={
            "HttpTokens": "optional",
            "HttpPutResponseHopLimit": 123,
            "HttpEndpoint": "disabled",
        },
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    assert launch_config["ClassicLinkVPCId"] == "vpc_id"
    assert launch_config["ClassicLinkVPCSecurityGroups"] == ["classic_sg1"]
    assert launch_config["EbsOptimized"] is True
    assert launch_config["AssociatePublicIpAddress"] is True
    assert launch_config["MetadataOptions"] == {
        "HttpTokens": "optional",
        "HttpPutResponseHopLimit": 123,
        "HttpEndpoint": "disabled",
    }


# The default AMIs are not loaded for our test case, to speed things up
# But we do need it for this specific test (and others in this file..)
@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_autoscaling
@mock_ec2
def test_create_launch_configuration_without_public_ip():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    ec2 = boto3.resource("ec2", "us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.0.0/27")

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    random_image_id = ec2_client.describe_images()["Images"][0]["ImageId"]

    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t1.micro",
        AssociatePublicIpAddress=False,
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    assert launch_config["AssociatePublicIpAddress"] is False

    asg_name = f"asg-{random_image_id}"
    client.create_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        LaunchConfigurationName=launch_config["LaunchConfigurationName"],
        MinSize=1,
        MaxSize=1,
        DesiredCapacity=1,
        VPCZoneIdentifier=subnet.id,
    )

    instances = client.describe_auto_scaling_instances()["AutoScalingInstances"]
    instance_id = instances[0]["InstanceId"]

    instance = ec2_client.describe_instances(InstanceIds=[instance_id])["Reservations"][
        0
    ]["Instances"][0]
    assert "PublicIpAddress" not in instance


@mock_autoscaling
def test_create_launch_configuration_additional_params_default_to_false():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t1.micro",
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    assert launch_config["EbsOptimized"] is False
    assert launch_config["AssociatePublicIpAddress"] is False


@mock_autoscaling
def test_create_launch_configuration_defaults():
    """Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes"""
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="m1.small",
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]

    # Defaults
    assert launch_config["KeyName"] == ""
    assert launch_config["SecurityGroups"] == []
    assert launch_config["UserData"] == ""
    assert launch_config["InstanceMonitoring"] == {"Enabled": False}
    assert "IamInstanceProfile" not in launch_config
    assert "SpotPrice" not in launch_config


@mock_autoscaling
def test_launch_configuration_describe_filter():
    client = boto3.client("autoscaling", region_name="us-east-1")
    for name in ["tester", "tester2", "tester3"]:
        client.create_launch_configuration(
            LaunchConfigurationName=name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="m1.small",
        )

    configs = client.describe_launch_configurations(
        LaunchConfigurationNames=["tester", "tester2"]
    )
    assert len(configs["LaunchConfigurations"]) == 2
    assert len(client.describe_launch_configurations()["LaunchConfigurations"]) == 3


@mock_autoscaling
def test_launch_configuration_describe_paginated():
    conn = boto3.client("autoscaling", region_name="us-east-1")
    for i in range(51):
        conn.create_launch_configuration(
            LaunchConfigurationName=f"TestLC{i}",
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )

    response = conn.describe_launch_configurations()
    lcs = response["LaunchConfigurations"]
    marker = response["NextToken"]
    assert len(lcs) == 50
    assert marker == lcs[-1]["LaunchConfigurationName"]

    response2 = conn.describe_launch_configurations(NextToken=marker)

    lcs.extend(response2["LaunchConfigurations"])
    assert len(lcs) == 51
    assert "NextToken" not in response2.keys()


@mock_autoscaling
def test_launch_configuration_delete():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="m1.small",
    )

    assert len(client.describe_launch_configurations()["LaunchConfigurations"]) == 1

    client.delete_launch_configuration(LaunchConfigurationName="tester")

    assert len(client.describe_launch_configurations()["LaunchConfigurations"]) == 0


@pytest.mark.parametrize(
    "request_params",
    [
        pytest.param(
            {"LaunchConfigurationName": "test"},
            id="No InstanceId, ImageId, or InstanceType parameters",
        ),
        pytest.param(
            {"LaunchConfigurationName": "test", "ImageId": "ami-test"},
            id="ImageId without InstanceType parameter",
        ),
        pytest.param(
            {"LaunchConfigurationName": "test", "InstanceType": "t2.medium"},
            id="InstanceType without ImageId parameter",
        ),
    ],
)
@mock_autoscaling
def test_invalid_launch_configuration_request_raises_error(request_params):
    client = boto3.client("autoscaling", region_name="us-east-1")
    with pytest.raises(ClientError) as ex:
        client.create_launch_configuration(**request_params)
    assert ex.value.response["Error"]["Code"] == "ValidationError"
    assert "Valid requests must contain" in ex.value.response["Error"]["Message"]


@mock.patch.dict(os.environ, {"MOTO_EC2_LOAD_DEFAULT_AMIS": "true"})
@mock_autoscaling
@mock_ec2
def test_launch_config_with_block_device_mappings__volumes_are_created():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't set environment variables in ServerMode")
    as_client = boto3.client("autoscaling", "us-east-2")
    ec2_client = boto3.client("ec2", "us-east-2")
    random_image_id = ec2_client.describe_images()["Images"][0]["ImageId"]

    as_client.create_launch_configuration(
        LaunchConfigurationName=f"lc-{random_image_id}",
        ImageId=random_image_id,
        InstanceType="t2.nano",
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sdf",
                "Ebs": {
                    "VolumeSize": 10,
                    "VolumeType": "standard",
                    "Encrypted": False,
                    "DeleteOnTermination": True,
                },
            }
        ],
    )

    asg_name = f"asg-{random_image_id}"
    as_client.create_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        LaunchConfigurationName=f"lc-{random_image_id}",
        MinSize=1,
        MaxSize=1,
        DesiredCapacity=1,
        AvailabilityZones=["us-east-2b"],
    )

    instances = as_client.describe_auto_scaling_instances()["AutoScalingInstances"]
    instance_id = instances[0]["InstanceId"]

    volumes = ec2_client.describe_volumes(
        Filters=[{"Name": "attachment.instance-id", "Values": [instance_id]}]
    )["Volumes"]
    assert len(volumes) == 2
    assert volumes[0]["Size"] == 8
    assert volumes[0]["Encrypted"] is False
    assert volumes[0]["VolumeType"] == "gp2"
    assert volumes[1]["Size"] == 10
    assert volumes[1]["Encrypted"] is False
    assert volumes[1]["VolumeType"] == "standard"
