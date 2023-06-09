import boto3
import pytest

from moto import mock_autoscaling

from .utils import setup_networking
from tests import EXAMPLE_AMI_ID


def setup_autoscale_group_boto3():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="tester",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="m1.small",
    )

    client.create_auto_scaling_group(
        AutoScalingGroupName="tester_group",
        LaunchConfigurationName="tester",
        MinSize=2,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )


@mock_autoscaling
def test_create_policy_boto3():
    setup_autoscale_group_boto3()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="ExactCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=3,
        Cooldown=60,
    )

    policy = client.describe_policies()["ScalingPolicies"][0]
    assert policy["PolicyName"] == "ScaleUp"
    assert policy["AdjustmentType"] == "ExactCapacity"
    assert policy["AutoScalingGroupName"] == "tester_group"
    assert policy["ScalingAdjustment"] == 3
    assert policy["Cooldown"] == 60


@mock_autoscaling
def test_create_policy_default_values_boto3():
    setup_autoscale_group_boto3()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="ExactCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=3,
    )

    policy = client.describe_policies()["ScalingPolicies"][0]
    assert policy["PolicyName"] == "ScaleUp"

    # Defaults
    assert policy["Cooldown"] == 300


@mock_autoscaling
def test_update_policy_boto3():
    setup_autoscale_group_boto3()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="ExactCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=3,
    )

    assert len(client.describe_policies()["ScalingPolicies"]) == 1
    policy = client.describe_policies()["ScalingPolicies"][0]
    assert policy["ScalingAdjustment"] == 3

    # Now update it by creating another with the same name
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="ExactCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=2,
    )
    assert len(client.describe_policies()["ScalingPolicies"]) == 1
    policy = client.describe_policies()["ScalingPolicies"][0]
    assert policy["ScalingAdjustment"] == 2


@mock_autoscaling
def test_delete_policy_boto3():
    setup_autoscale_group_boto3()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="ExactCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=3,
    )

    assert len(client.describe_policies()["ScalingPolicies"]) == 1

    client.delete_policy(PolicyName="ScaleUp")
    assert len(client.describe_policies()["ScalingPolicies"]) == 0


@mock_autoscaling
def test_execute_policy_exact_capacity_boto3():
    setup_autoscale_group_boto3()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="ExactCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=3,
    )

    client.execute_policy(PolicyName="ScaleUp")

    instances = client.describe_auto_scaling_instances()
    assert len(instances["AutoScalingInstances"]) == 3


@mock_autoscaling
def test_execute_policy_positive_change_in_capacity_boto3():
    setup_autoscale_group_boto3()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="ChangeInCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=3,
    )

    client.execute_policy(PolicyName="ScaleUp")

    instances = client.describe_auto_scaling_instances()
    assert len(instances["AutoScalingInstances"]) == 5


@pytest.mark.parametrize(
    "adjustment,nr_of_instances", [(1, 3), (50, 3), (100, 4), (250, 7)]
)
@mock_autoscaling
def test_execute_policy_percent_change_in_capacity_boto3(adjustment, nr_of_instances):
    """http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
    If PercentChangeInCapacity returns a value between 0 and 1,
    Auto Scaling will round it off to 1."""
    setup_autoscale_group_boto3()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.put_scaling_policy(
        PolicyName="ScaleUp",
        AdjustmentType="PercentChangeInCapacity",
        AutoScalingGroupName="tester_group",
        ScalingAdjustment=adjustment,
    )

    client.execute_policy(PolicyName="ScaleUp")

    instances = client.describe_auto_scaling_instances()
    assert len(instances["AutoScalingInstances"]) == nr_of_instances
