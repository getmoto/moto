from __future__ import unicode_literals
import boto
import boto3
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping

import sure  # noqa

from moto import mock_autoscaling_deprecated
from moto import mock_autoscaling
from tests.helpers import requires_boto_gte


@mock_autoscaling_deprecated
def test_create_launch_configuration():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='t1.micro',
        key_name='the_keys',
        security_groups=["default", "default2"],
        user_data=b"This is some user_data",
        instance_monitoring=True,
        instance_profile_name='arn:aws:iam::123456789012:instance-profile/testing',
        spot_price=0.1,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal('tester')
    launch_config.image_id.should.equal('ami-abcd1234')
    launch_config.instance_type.should.equal('t1.micro')
    launch_config.key_name.should.equal('the_keys')
    set(launch_config.security_groups).should.equal(
        set(['default', 'default2']))
    launch_config.user_data.should.equal(b"This is some user_data")
    launch_config.instance_monitoring.enabled.should.equal('true')
    launch_config.instance_profile_name.should.equal(
        'arn:aws:iam::123456789012:instance-profile/testing')
    launch_config.spot_price.should.equal(0.1)


@requires_boto_gte("2.27.0")
@mock_autoscaling_deprecated
def test_create_launch_configuration_with_block_device_mappings():
    block_device_mapping = BlockDeviceMapping()

    ephemeral_drive = BlockDeviceType()
    ephemeral_drive.ephemeral_name = 'ephemeral0'
    block_device_mapping['/dev/xvdb'] = ephemeral_drive

    snapshot_drive = BlockDeviceType()
    snapshot_drive.snapshot_id = "snap-1234abcd"
    snapshot_drive.volume_type = "standard"
    block_device_mapping['/dev/xvdp'] = snapshot_drive

    ebs_drive = BlockDeviceType()
    ebs_drive.volume_type = "io1"
    ebs_drive.size = 100
    ebs_drive.iops = 1000
    ebs_drive.delete_on_termination = False
    block_device_mapping['/dev/xvdh'] = ebs_drive

    conn = boto.connect_autoscale(use_block_device_types=True)
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
        key_name='the_keys',
        security_groups=["default", "default2"],
        user_data=b"This is some user_data",
        instance_monitoring=True,
        instance_profile_name='arn:aws:iam::123456789012:instance-profile/testing',
        spot_price=0.1,
        block_device_mappings=[block_device_mapping]
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal('tester')
    launch_config.image_id.should.equal('ami-abcd1234')
    launch_config.instance_type.should.equal('m1.small')
    launch_config.key_name.should.equal('the_keys')
    set(launch_config.security_groups).should.equal(
        set(['default', 'default2']))
    launch_config.user_data.should.equal(b"This is some user_data")
    launch_config.instance_monitoring.enabled.should.equal('true')
    launch_config.instance_profile_name.should.equal(
        'arn:aws:iam::123456789012:instance-profile/testing')
    launch_config.spot_price.should.equal(0.1)
    len(launch_config.block_device_mappings).should.equal(3)

    returned_mapping = launch_config.block_device_mappings

    set(returned_mapping.keys()).should.equal(
        set(['/dev/xvdb', '/dev/xvdp', '/dev/xvdh']))

    returned_mapping['/dev/xvdh'].iops.should.equal(1000)
    returned_mapping['/dev/xvdh'].size.should.equal(100)
    returned_mapping['/dev/xvdh'].volume_type.should.equal("io1")
    returned_mapping['/dev/xvdh'].delete_on_termination.should.be.false

    returned_mapping['/dev/xvdp'].snapshot_id.should.equal("snap-1234abcd")
    returned_mapping['/dev/xvdp'].volume_type.should.equal("standard")

    returned_mapping['/dev/xvdb'].ephemeral_name.should.equal('ephemeral0')


@requires_boto_gte("2.12")
@mock_autoscaling_deprecated
def test_create_launch_configuration_for_2_12():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        ebs_optimized=True,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.ebs_optimized.should.equal(True)


@requires_boto_gte("2.25.0")
@mock_autoscaling_deprecated
def test_create_launch_configuration_using_ip_association():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        associate_public_ip_address=True,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.associate_public_ip_address.should.equal(True)


@requires_boto_gte("2.25.0")
@mock_autoscaling_deprecated
def test_create_launch_configuration_using_ip_association_should_default_to_false():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.associate_public_ip_address.should.equal(False)


@mock_autoscaling_deprecated
def test_create_launch_configuration_defaults():
    """ Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes """
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal('tester')
    launch_config.image_id.should.equal('ami-abcd1234')
    launch_config.instance_type.should.equal('m1.small')

    # Defaults
    launch_config.key_name.should.equal('')
    list(launch_config.security_groups).should.equal([])
    launch_config.user_data.should.equal(b"")
    launch_config.instance_monitoring.enabled.should.equal('false')
    launch_config.instance_profile_name.should.equal(None)
    launch_config.spot_price.should.equal(None)


@requires_boto_gte("2.12")
@mock_autoscaling_deprecated
def test_create_launch_configuration_defaults_for_2_12():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.ebs_optimized.should.equal(False)


@mock_autoscaling_deprecated
def test_launch_configuration_describe_filter():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)
    config.name = 'tester2'
    conn.create_launch_configuration(config)
    config.name = 'tester3'
    conn.create_launch_configuration(config)

    conn.get_all_launch_configurations(
        names=['tester', 'tester2']).should.have.length_of(2)
    conn.get_all_launch_configurations().should.have.length_of(3)


@mock_autoscaling
def test_launch_configuration_describe_paginated():
    conn = boto3.client('autoscaling', region_name='us-east-1')
    for i in range(51):
        conn.create_launch_configuration(LaunchConfigurationName='TestLC%d' % i)

    response = conn.describe_launch_configurations()
    lcs = response["LaunchConfigurations"]
    marker = response["NextToken"]
    lcs.should.have.length_of(50)
    marker.should.equal(lcs[-1]['LaunchConfigurationName'])

    response2 = conn.describe_launch_configurations(NextToken=marker)

    lcs.extend(response2["LaunchConfigurations"])
    lcs.should.have.length_of(51)
    assert 'NextToken' not in response2.keys()


@mock_autoscaling_deprecated
def test_launch_configuration_delete():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    conn.get_all_launch_configurations().should.have.length_of(1)

    conn.delete_launch_configuration('tester')
    conn.get_all_launch_configurations().should.have.length_of(0)
