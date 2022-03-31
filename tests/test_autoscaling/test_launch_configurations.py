import base64
import boto3
from botocore.exceptions import ClientError

import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_autoscaling
from moto.core import ACCOUNT_ID
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
    xvdp["Ebs"]["DeleteOnTermination"].should.equal(False)

    xvdb["VirtualName"].should.equal("ephemeral0")
    xvdb.shouldnt.have.key("Ebs")


@mock_autoscaling
def test_create_launch_configuration_additional_parameters():
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t1.micro",
        EbsOptimized=True,
        AssociatePublicIpAddress=True,
    )

    launch_config = client.describe_launch_configurations()["LaunchConfigurations"][0]
    launch_config["EbsOptimized"].should.equal(True)
    launch_config["AssociatePublicIpAddress"].should.equal(True)


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
