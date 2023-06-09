import boto3

from moto import mock_autoscaling, mock_elb, mock_ec2

from .utils import setup_networking
from tests import EXAMPLE_AMI_ID


@mock_autoscaling
@mock_ec2
@mock_elb
def test_enable_metrics_collection():
    mocked_networking = setup_networking()
    elb_client = boto3.client("elb", region_name="us-east-1")
    elb_client.create_load_balancer(
        LoadBalancerName="test_lb",
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=[],
    )

    as_client = boto3.client("autoscaling", region_name="us-east-1")
    as_client.create_launch_configuration(
        LaunchConfigurationName="tester_config",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )

    as_client.create_auto_scaling_group(
        AutoScalingGroupName="tester_group",
        LaunchConfigurationName="tester_config",
        MinSize=2,
        MaxSize=2,
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    as_client.enable_metrics_collection(
        AutoScalingGroupName="tester_group",
        Metrics=["GroupMinSize"],
        Granularity="1Minute",
    )

    resp = as_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=["tester_group"]
    )["AutoScalingGroups"][0]
    assert len(resp["EnabledMetrics"]) == 1
    assert resp["EnabledMetrics"][0] == {
        "Metric": "GroupMinSize",
        "Granularity": "1Minute",
    }
