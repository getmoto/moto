import boto
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from nose.plugins.attrib import attr
import sure  # flake8: noqa
from unittest import skipIf

from moto import mock_autoscaling, mock_ec2
from tests.helpers import requires_boto_gte


@mock_autoscaling
def test_create_autoscaling_group():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal('tester_group')
    set(group.availability_zones).should.equal(set(['us-east-1c', 'us-east-1b']))
    group.desired_capacity.should.equal(2)
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.vpc_zone_identifier.should.equal('subnet-1234abcd')
    group.launch_config_name.should.equal('tester')


@mock_autoscaling
def test_create_autoscaling_groups_defaults():
    """ Test with the minimum inputs and check that all of the proper defaults
    are assigned for the other attributes """
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.name.should.equal('tester_group')
    group.max_size.should.equal(2)
    group.min_size.should.equal(2)
    group.launch_config_name.should.equal('tester')

    # Defaults
    list(group.availability_zones).should.equal([])
    group.desired_capacity.should.equal(2)
    group.vpc_zone_identifier.should.equal('')


@mock_autoscaling
def test_autoscaling_group_describe_filter():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)
    group.name = 'tester_group2'
    conn.create_auto_scaling_group(group)
    group.name = 'tester_group3'
    conn.create_auto_scaling_group(group)

    conn.get_all_groups(names=['tester_group', 'tester_group2']).should.have.length_of(2)
    conn.get_all_groups().should.have.length_of(3)


@mock_autoscaling
def test_autoscaling_update():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.vpc_zone_identifier.should.equal('subnet-1234abcd')

    group.vpc_zone_identifier = 'subnet-5678efgh'
    group.update()

    group = conn.get_all_groups()[0]
    group.vpc_zone_identifier.should.equal('subnet-5678efgh')


@mock_autoscaling
def test_autoscaling_group_delete():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)

    conn.get_all_groups().should.have.length_of(1)

    conn.delete_auto_scaling_group('tester_group')
    conn.get_all_groups().should.have.length_of(0)


@mock_ec2
@mock_autoscaling
def test_autoscaling_group_describe_instances():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        max_size=2,
        min_size=2,
        launch_config=config,
    )
    conn.create_auto_scaling_group(group)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)
    instances[0].launch_config_name.should.equal('tester')
    autoscale_instance_ids = [instance.instance_id for instance in instances]

    ec2_conn = boto.connect_ec2()
    reservations = ec2_conn.get_all_instances()
    instances = reservations[0].instances
    instances.should.have.length_of(2)
    instance_ids = [instance.id for instance in instances]
    set(autoscale_instance_ids).should.equal(set(instance_ids))


@requires_boto_gte("2.8")
@mock_autoscaling
def test_set_desired_capacity_up():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 3)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(3)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)


@requires_boto_gte("2.8")
@mock_autoscaling
def test_set_desired_capacity_down():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 1)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(1)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(1)


@requires_boto_gte("2.8")
@mock_autoscaling
def test_set_desired_capacity_the_same():
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name='tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name='tester_group',
        availability_zones=['us-east-1c', 'us-east-1b'],
        desired_capacity=2,
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier='subnet-1234abcd',
    )
    conn.create_auto_scaling_group(group)

    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)
    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)

    conn.set_desired_capacity("tester_group", 2)
    group = conn.get_all_groups()[0]
    group.desired_capacity.should.equal(2)

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(2)
