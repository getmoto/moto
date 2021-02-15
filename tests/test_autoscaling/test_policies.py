from __future__ import unicode_literals
import boto
from boto.ec2.autoscale.launchconfig import LaunchConfiguration
from boto.ec2.autoscale.group import AutoScalingGroup
from boto.ec2.autoscale.policy import ScalingPolicy
import sure  # noqa

from moto import mock_autoscaling_deprecated

from .utils import setup_networking_deprecated
from tests import EXAMPLE_AMI_ID


def setup_autoscale_group():
    mocked_networking = setup_networking_deprecated()
    conn = boto.connect_autoscale()
    config = LaunchConfiguration(
        name="tester", image_id=EXAMPLE_AMI_ID, instance_type="m1.small"
    )
    conn.create_launch_configuration(config)

    group = AutoScalingGroup(
        name="tester_group",
        max_size=2,
        min_size=2,
        launch_config=config,
        vpc_zone_identifier=mocked_networking["subnet1"],
    )
    conn.create_auto_scaling_group(group)
    return group


@mock_autoscaling_deprecated
def test_create_policy():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="ExactCapacity",
        as_name="tester_group",
        scaling_adjustment=3,
        cooldown=60,
    )
    conn.create_scaling_policy(policy)

    policy = conn.get_all_policies()[0]
    policy.name.should.equal("ScaleUp")
    policy.adjustment_type.should.equal("ExactCapacity")
    policy.as_name.should.equal("tester_group")
    policy.scaling_adjustment.should.equal(3)
    policy.cooldown.should.equal(60)


@mock_autoscaling_deprecated
def test_create_policy_default_values():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="ExactCapacity",
        as_name="tester_group",
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    policy = conn.get_all_policies()[0]
    policy.name.should.equal("ScaleUp")

    # Defaults
    policy.cooldown.should.equal(300)


@mock_autoscaling_deprecated
def test_update_policy():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="ExactCapacity",
        as_name="tester_group",
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    policy = conn.get_all_policies()[0]
    policy.scaling_adjustment.should.equal(3)

    # Now update it by creating another with the same name
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="ExactCapacity",
        as_name="tester_group",
        scaling_adjustment=2,
    )
    conn.create_scaling_policy(policy)
    policy = conn.get_all_policies()[0]
    policy.scaling_adjustment.should.equal(2)


@mock_autoscaling_deprecated
def test_delete_policy():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="ExactCapacity",
        as_name="tester_group",
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    conn.get_all_policies().should.have.length_of(1)

    conn.delete_policy("ScaleUp")
    conn.get_all_policies().should.have.length_of(0)


@mock_autoscaling_deprecated
def test_execute_policy_exact_capacity():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="ExactCapacity",
        as_name="tester_group",
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)


@mock_autoscaling_deprecated
def test_execute_policy_positive_change_in_capacity():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="ChangeInCapacity",
        as_name="tester_group",
        scaling_adjustment=3,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(5)


@mock_autoscaling_deprecated
def test_execute_policy_percent_change_in_capacity():
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="PercentChangeInCapacity",
        as_name="tester_group",
        scaling_adjustment=50,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)


@mock_autoscaling_deprecated
def test_execute_policy_small_percent_change_in_capacity():
    """http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
    If PercentChangeInCapacity returns a value between 0 and 1,
    Auto Scaling will round it off to 1."""
    setup_autoscale_group()
    conn = boto.connect_autoscale()
    policy = ScalingPolicy(
        name="ScaleUp",
        adjustment_type="PercentChangeInCapacity",
        as_name="tester_group",
        scaling_adjustment=1,
    )
    conn.create_scaling_policy(policy)

    conn.execute_policy("ScaleUp")

    instances = list(conn.get_all_autoscaling_instances())
    instances.should.have.length_of(3)
