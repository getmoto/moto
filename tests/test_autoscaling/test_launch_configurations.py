import base64

import boto
import boto3
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping
from botocore.exceptions import ClientError

import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_autoscaling_deprecated
from moto import mock_autoscaling
from moto.core import ACCOUNT_ID
from tests.helpers import requires_boto_gte
from tests import EXAMPLE_AMI_ID


# Has boto3 equivalent
@mock_autoscaling_deprecated
def test_create_launch_configuration():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester",
        image_id="ami-abcd1234",
        instance_type="t1.micro",
        key_name="the_keys",
        security_groups=["default", "default2"],
        user_data=b"This is some user_data",
        instance_monitoring=True,
        instance_profile_name="arn:aws:iam::{}:instance-profile/testing".format(
            ACCOUNT_ID
        ),
        spot_price=0.1,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal("tester")
    launch_config.image_id.should.equal("ami-abcd1234")
    launch_config.instance_type.should.equal("t1.micro")
    launch_config.key_name.should.equal("the_keys")
    set(launch_config.security_groups).should.equal(set(["default", "default2"]))
    launch_config.user_data.should.equal(b"This is some user_data")
    launch_config.instance_monitoring.enabled.should.equal("true")
    launch_config.instance_profile_name.should.equal(
        "arn:aws:iam::{}:instance-profile/testing".format(ACCOUNT_ID)
    )
    launch_config.spot_price.should.equal(0.1)


@mock_autoscaling
def test_create_launch_configuration_boto3():
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


# Has boto3 equivalent
@requires_boto_gte("2.27.0")
@mock_autoscaling_deprecated
def test_create_launch_configuration_with_block_device_mappings():
    block_device_mapping = BlockDeviceMapping()

    ephemeral_drive = BlockDeviceType()
    ephemeral_drive.ephemeral_name = "ephemeral0"
    block_device_mapping["/dev/xvdb"] = ephemeral_drive

    snapshot_drive = BlockDeviceType()
    snapshot_drive.snapshot_id = "snap-1234abcd"
    snapshot_drive.volume_type = "standard"
    block_device_mapping["/dev/xvdp"] = snapshot_drive

    ebs_drive = BlockDeviceType()
    ebs_drive.volume_type = "io1"
    ebs_drive.size = 100
    ebs_drive.iops = 1000
    ebs_drive.delete_on_termination = False
    block_device_mapping["/dev/xvdh"] = ebs_drive

    conn = boto.connect_autoscale(use_block_device_types=True)
    config = LaunchConfiguration(
        name="tester",
        image_id="ami-abcd1234",
        instance_type="m1.small",
        key_name="the_keys",
        security_groups=["default", "default2"],
        user_data=b"This is some user_data",
        instance_monitoring=True,
        instance_profile_name="arn:aws:iam::{}:instance-profile/testing".format(
            ACCOUNT_ID
        ),
        spot_price=0.1,
        block_device_mappings=[block_device_mapping],
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal("tester")
    launch_config.image_id.should.equal("ami-abcd1234")
    launch_config.instance_type.should.equal("m1.small")
    launch_config.key_name.should.equal("the_keys")
    set(launch_config.security_groups).should.equal(set(["default", "default2"]))
    launch_config.user_data.should.equal(b"This is some user_data")
    launch_config.instance_monitoring.enabled.should.equal("true")
    launch_config.instance_profile_name.should.equal(
        "arn:aws:iam::{}:instance-profile/testing".format(ACCOUNT_ID)
    )
    launch_config.spot_price.should.equal(0.1)
    len(launch_config.block_device_mappings).should.equal(3)

    returned_mapping = launch_config.block_device_mappings

    set(returned_mapping.keys()).should.equal(
        set(["/dev/xvdb", "/dev/xvdp", "/dev/xvdh"])
    )

    returned_mapping["/dev/xvdh"].iops.should.equal(1000)
    returned_mapping["/dev/xvdh"].size.should.equal(100)
    returned_mapping["/dev/xvdh"].volume_type.should.equal("io1")
    returned_mapping["/dev/xvdh"].delete_on_termination.should.be.false

    returned_mapping["/dev/xvdp"].snapshot_id.should.equal("snap-1234abcd")
    returned_mapping["/dev/xvdp"].volume_type.should.equal("standard")

    returned_mapping["/dev/xvdb"].ephemeral_name.should.equal("ephemeral0")


@mock_autoscaling
def test_create_launch_configuration_with_block_device_mappings_boto3():
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


# Has boto3 equivalent
@requires_boto_gte("2.12")
@mock_autoscaling_deprecated
def test_create_launch_configuration_for_2_12():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", ebs_optimized=True
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.ebs_optimized.should.equal(True)


# Has boto3 equivalent
@requires_boto_gte("2.25.0")
@mock_autoscaling_deprecated
def test_create_launch_configuration_using_ip_association():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", associate_public_ip_address=True
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.associate_public_ip_address.should.equal(True)


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


# Has boto3 equivalent
@requires_boto_gte("2.25.0")
@mock_autoscaling_deprecated
def test_create_launch_configuration_using_ip_association_should_default_to_false():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(name="tester", image_id="ami-abcd1234")
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.associate_public_ip_address.should.equal(False)


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


# Has boto3 equivalent
@mock_autoscaling_deprecated
def test_create_launch_configuration_defaults():
    """Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes"""
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="m1.small"
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal("tester")
    launch_config.image_id.should.equal("ami-abcd1234")
    launch_config.instance_type.should.equal("m1.small")

    # Defaults
    launch_config.key_name.should.equal("")
    list(launch_config.security_groups).should.equal([])
    launch_config.user_data.should.equal(b"")
    launch_config.instance_monitoring.enabled.should.equal("false")
    launch_config.instance_profile_name.should.equal(None)
    launch_config.spot_price.should.equal(None)


@mock_autoscaling
def test_create_launch_configuration_defaults_boto3():
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


# Has boto3 equivalent
@requires_boto_gte("2.12")
@mock_autoscaling_deprecated
def test_create_launch_configuration_defaults_for_2_12():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(name="tester", image_id="ami-abcd1234")
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.ebs_optimized.should.equal(False)


# Has boto3 equivalent
@mock_autoscaling_deprecated
def test_launch_configuration_describe_filter():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="m1.small"
    )
    conn.create_launch_configuration(config)
    config.name = "tester2"
    conn.create_launch_configuration(config)
    config.name = "tester3"
    conn.create_launch_configuration(config)

    conn.get_all_launch_configurations(
        names=["tester", "tester2"]
    ).should.have.length_of(2)
    conn.get_all_launch_configurations().should.have.length_of(3)


@mock_autoscaling
def test_launch_configuration_describe_filter_boto3():
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


# Has boto3 equivalent
@mock_autoscaling_deprecated
def test_launch_configuration_delete():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id="ami-abcd1234", instance_type="m1.small"
    )
    conn.create_launch_configuration(config)

    conn.get_all_launch_configurations().should.have.length_of(1)

    conn.delete_launch_configuration("tester")
    conn.get_all_launch_configurations().should.have.length_of(0)


@mock_autoscaling
def test_launch_configuration_delete_boto3():
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
