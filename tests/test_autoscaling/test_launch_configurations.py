import boto
from boto.ec2.autoscale.launchconfig import LaunchConfiguration

import sure  # noqa

from moto import mock_autoscaling
from tests.helpers import requires_boto_gte


@mock_autoscaling
def test_create_launch_configuration():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
        key_name='the_keys',
        security_groups=["default", "default2"],
        user_data="This is some user_data",
        instance_monitoring=True,
        instance_profile_name='arn:aws:iam::123456789012:instance-profile/testing',
        spot_price=0.1,
        ebs_optimized=True,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.name.should.equal('tester')
    launch_config.image_id.should.equal('ami-abcd1234')
    launch_config.instance_type.should.equal('m1.small')
    launch_config.key_name.should.equal('the_keys')
    set(launch_config.security_groups).should.equal(set(['default', 'default2']))
    launch_config.user_data.should.equal("This is some user_data")
    launch_config.instance_monitoring.enabled.should.equal('true')
    launch_config.instance_profile_name.should.equal('arn:aws:iam::123456789012:instance-profile/testing')
    launch_config.spot_price.should.equal(0.1)
    launch_config.ebs_optimized.should.equal(True)


@requires_boto_gte("2.12")
@mock_autoscaling
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


@mock_autoscaling
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
    launch_config.user_data.should.equal("")
    launch_config.instance_monitoring.enabled.should.equal('false')
    launch_config.instance_profile_name.should.equal(None)
    launch_config.spot_price.should.equal(None)
    launch_config.ebs_optimized.should.equal(False)


@requires_boto_gte("2.12")
@mock_autoscaling
def test_create_launch_configuration_defaults_for_2_12():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        ebs_optimized=True,
    )
    conn.create_launch_configuration(config)

    launch_config = conn.get_all_launch_configurations()[0]
    launch_config.ebs_optimized.should.equal(False)


@mock_autoscaling
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

    conn.get_all_launch_configurations(names=['tester', 'tester2']).should.have.length_of(2)
    conn.get_all_launch_configurations().should.have.length_of(3)


@mock_autoscaling
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
