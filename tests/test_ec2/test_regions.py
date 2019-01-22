from __future__ import unicode_literals
import boto.ec2
import boto.ec2.autoscale
import boto.ec2.elb
import sure
from moto import mock_ec2_deprecated, mock_autoscaling_deprecated, mock_elb_deprecated

from moto.ec2 import ec2_backends

def test_use_boto_regions():
    boto_regions = {r.name for r in boto.ec2.regions()}
    moto_regions = set(ec2_backends)

    moto_regions.should.equal(boto_regions)

def add_servers_to_region(ami_id, count, region):
    conn = boto.ec2.connect_to_region(region)
    for index in range(count):
        conn.run_instances(ami_id)

@mock_ec2_deprecated
def test_add_servers_to_a_single_region():
    region = 'ap-northeast-1'
    add_servers_to_region('ami-1234abcd', 1, region)
    add_servers_to_region('ami-5678efgh', 1, region)

    conn = boto.ec2.connect_to_region(region)
    reservations = conn.get_all_instances()
    len(reservations).should.equal(2)
    reservations.sort(key=lambda x: x.instances[0].image_id)

    reservations[0].instances[0].image_id.should.equal('ami-1234abcd')
    reservations[1].instances[0].image_id.should.equal('ami-5678efgh')


@mock_ec2_deprecated
def test_add_servers_to_multiple_regions():
    region1 = 'us-east-1'
    region2 = 'ap-northeast-1'
    add_servers_to_region('ami-1234abcd', 1, region1)
    add_servers_to_region('ami-5678efgh', 1, region2)

    us_conn = boto.ec2.connect_to_region(region1)
    ap_conn = boto.ec2.connect_to_region(region2)
    us_reservations = us_conn.get_all_instances()
    ap_reservations = ap_conn.get_all_instances()

    len(us_reservations).should.equal(1)
    len(ap_reservations).should.equal(1)

    us_reservations[0].instances[0].image_id.should.equal('ami-1234abcd')
    ap_reservations[0].instances[0].image_id.should.equal('ami-5678efgh')


@mock_autoscaling_deprecated
@mock_elb_deprecated
def test_create_autoscaling_group():
    elb_conn = boto.ec2.elb.connect_to_region('us-east-1')
    elb_conn.create_load_balancer(
        'us_test_lb', zones=[], listeners=[(80, 8080, 'http')])
    elb_conn = boto.ec2.elb.connect_to_region('ap-northeast-1')
    elb_conn.create_load_balancer(
        'ap_test_lb', zones=[], listeners=[(80, 8080, 'http')])

    us_conn = boto.ec2.autoscale.connect_to_region('us-east-1')
    config = boto.ec2.autoscale.LaunchConfiguration(
        name='us_tester',
        image_id='ami-abcd1234',
        instance_type='m1.small',
    )
    x = us_conn.create_launch_configuration(config)

    us_subnet_id = list(ec2_backends['us-east-1'].subnets['us-east-1c'].keys())[0]
    ap_subnet_id = list(ec2_backends['ap-northeast-1'].subnets['ap-northeast-1a'].keys())[0]
    group = boto.ec2.autoscale.AutoScalingGroup(
        name='us_tester_group',
        availability_zones=['us-east-1c'],
        default_cooldown=60,
        desired_capacity=2,
        health_check_period=100,
        health_check_type="EC2",
        max_size=2,
        min_size=2,
        launch_config=config,
        load_balancers=["us_test_lb"],
        placement_group="us_test_placement",
        vpc_zone_identifier=us_subnet_id,
        termination_policies=["OldestInstance", "NewestInstance"],
    )
    us_conn.create_auto_scaling_group(group)

    ap_conn = boto.ec2.autoscale.connect_to_region('ap-northeast-1')
    config = boto.ec2.autoscale.LaunchConfiguration(
        name='ap_tester',
        image_id='ami-efgh5678',
        instance_type='m1.small',
    )
    ap_conn.create_launch_configuration(config)

    group = boto.ec2.autoscale.AutoScalingGroup(
        name='ap_tester_group',
        availability_zones=['ap-northeast-1a'],
        default_cooldown=60,
        desired_capacity=2,
        health_check_period=100,
        health_check_type="EC2",
        max_size=2,
        min_size=2,
        launch_config=config,
        load_balancers=["ap_test_lb"],
        placement_group="ap_test_placement",
        vpc_zone_identifier=ap_subnet_id,
        termination_policies=["OldestInstance", "NewestInstance"],
    )
    ap_conn.create_auto_scaling_group(group)

    len(us_conn.get_all_groups()).should.equal(1)
    len(ap_conn.get_all_groups()).should.equal(1)

    us_group = us_conn.get_all_groups()[0]
    us_group.name.should.equal('us_tester_group')
    list(us_group.availability_zones).should.equal(['us-east-1c'])
    us_group.desired_capacity.should.equal(2)
    us_group.max_size.should.equal(2)
    us_group.min_size.should.equal(2)
    us_group.vpc_zone_identifier.should.equal(us_subnet_id)
    us_group.launch_config_name.should.equal('us_tester')
    us_group.default_cooldown.should.equal(60)
    us_group.health_check_period.should.equal(100)
    us_group.health_check_type.should.equal("EC2")
    list(us_group.load_balancers).should.equal(["us_test_lb"])
    us_group.placement_group.should.equal("us_test_placement")
    list(us_group.termination_policies).should.equal(
        ["OldestInstance", "NewestInstance"])

    ap_group = ap_conn.get_all_groups()[0]
    ap_group.name.should.equal('ap_tester_group')
    list(ap_group.availability_zones).should.equal(['ap-northeast-1a'])
    ap_group.desired_capacity.should.equal(2)
    ap_group.max_size.should.equal(2)
    ap_group.min_size.should.equal(2)
    ap_group.vpc_zone_identifier.should.equal(ap_subnet_id)
    ap_group.launch_config_name.should.equal('ap_tester')
    ap_group.default_cooldown.should.equal(60)
    ap_group.health_check_period.should.equal(100)
    ap_group.health_check_type.should.equal("EC2")
    list(ap_group.load_balancers).should.equal(["ap_test_lb"])
    ap_group.placement_group.should.equal("ap_test_placement")
    list(ap_group.termination_policies).should.equal(
        ["OldestInstance", "NewestInstance"])
