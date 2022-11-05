import base64
import boto3
from botocore.exceptions import ClientError

import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_autoscaling, mock_ec2
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID


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
        IamInstanceProfile="arn:aws:iam::{}:instance-profile/testing".format(
            ACCOUNT_ID
        ),
        SpotPrice="0.1",
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    launch_config["LaunchConfigurationName"].should.equal("tester")
    launch_config.should.have.key("LaunchConfigurationARN")
    launch_config["ImageId"].should.equal(EXAMPLE_AMI_ID)
    launch_config["InstanceType"].should.equal("t1.micro")
    launch_config["KeyName"].should.equal("the_keys")
    set(launch_config["SecurityGroups"]).should.equal(set(["default", "default2"]))
    userdata = launch_config["UserData"]
    userdata = base64.b64decode(userdata)
    userdata.should.equal(b"This is some user_data")
    launch_config["InstanceMonitoring"].should.equal({"Enabled": True})
    launch_config["IamInstanceProfile"].should.equal(
        "arn:aws:iam::{}:instance-profile/testing".format(ACCOUNT_ID)
    )
    launch_config["SpotPrice"].should.equal("0.1")
    launch_config["BlockDeviceMappings"].should.equal([])


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
        IamInstanceProfile="arn:aws:iam::{}:instance-profile/testing".format(
            ACCOUNT_ID
        ),
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
    launch_config["LaunchConfigurationName"].should.equal("tester")

    mappings = launch_config["BlockDeviceMappings"]
    mappings.should.have.length_of(3)

    xvdh = [m for m in mappings if m["DeviceName"] == "/dev/xvdh"][0]
    xvdp = [m for m in mappings if m["DeviceName"] == "/dev/xvdp"][0]
    xvdb = [m for m in mappings if m["DeviceName"] == "/dev/xvdb"][0]

    xvdh.shouldnt.have.key("VirtualName")
    xvdh.should.have.key("Ebs")
    xvdh["Ebs"]["VolumeSize"].should.equal(100)
    xvdh["Ebs"]["VolumeType"].should.equal("io1")
    xvdh["Ebs"]["DeleteOnTermination"].should.equal(False)
    xvdh["Ebs"]["Iops"].should.equal(1000)

    xvdp.shouldnt.have.key("VirtualName")
    xvdp.should.have.key("Ebs")
    xvdp["Ebs"]["SnapshotId"].should.equal("snap-1234abcd")
    xvdp["Ebs"]["VolumeType"].should.equal("standard")

    xvdb["VirtualName"].should.equal("ephemeral0")
    xvdb.shouldnt.have.key("Ebs")


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
    launch_config["ClassicLinkVPCId"].should.equal("vpc_id")
    launch_config["ClassicLinkVPCSecurityGroups"].should.equal(["classic_sg1"])
    launch_config["EbsOptimized"].should.equal(True)
    launch_config["AssociatePublicIpAddress"].should.equal(True)
    launch_config["MetadataOptions"].should.equal(
        {
            "HttpTokens": "optional",
            "HttpPutResponseHopLimit": 123,
            "HttpEndpoint": "disabled",
        }
    )


@mock_autoscaling
@mock_ec2
def test_create_launch_configuration_without_public_ip():
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
    launch_config["AssociatePublicIpAddress"].should.equal(False)

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
    instance.shouldnt.have.key("PublicIpAddress")


@mock_autoscaling
def test_create_launch_configuration_additional_params_default_to_false():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t1.micro",
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    launch_config["EbsOptimized"].should.equal(False)
    launch_config["AssociatePublicIpAddress"].should.equal(False)


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
    launch_config["KeyName"].should.equal("")
    launch_config["SecurityGroups"].should.equal([])
    launch_config["UserData"].should.equal("")
    launch_config["InstanceMonitoring"].should.equal({"Enabled": False})
    launch_config.shouldnt.have.key("IamInstanceProfile")
    launch_config.shouldnt.have.key("SpotPrice")


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
    configs["LaunchConfigurations"].should.have.length_of(2)
    client.describe_launch_configurations()[
        "LaunchConfigurations"
    ].should.have.length_of(3)


@mock_autoscaling
def test_launch_configuration_describe_paginated():
    conn = boto3.client("autoscaling", region_name="us-east-1")
    for i in range(51):
        conn.create_launch_configuration(
            LaunchConfigurationName="TestLC%d" % i,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )

    response = conn.describe_launch_configurations()
    lcs = response["LaunchConfigurations"]
    marker = response["NextToken"]
    lcs.should.have.length_of(50)
    marker.should.equal(lcs[-1]["LaunchConfigurationName"])

    response2 = conn.describe_launch_configurations(NextToken=marker)

    lcs.extend(response2["LaunchConfigurations"])
    lcs.should.have.length_of(51)
    assert "NextToken" not in response2.keys()


@mock_autoscaling
def test_launch_configuration_delete():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="m1.small",
    )

    client.describe_launch_configurations()[
        "LaunchConfigurations"
    ].should.have.length_of(1)

    client.delete_launch_configuration(LaunchConfigurationName="tester")

    client.describe_launch_configurations()[
        "LaunchConfigurations"
    ].should.have.length_of(0)


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
    ex.value.response["Error"]["Code"].should.equal("ValidationError")
    ex.value.response["Error"]["Message"].should.match(
        r"^Valid requests must contain.*"
    )


@mock_autoscaling
@mock_ec2
def test_launch_config_with_block_device_mappings__volumes_are_created():
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
    volumes.should.have.length_of(2)
    volumes[0].should.have.key("Size").equals(8)
    volumes[0].should.have.key("Encrypted").equals(False)
    volumes[0].should.have.key("VolumeType").equals("gp2")
    volumes[1].should.have.key("Size").equals(10)
    volumes[1].should.have.key("Encrypted").equals(False)
    volumes[1].should.have.key("VolumeType").equals("standard")
