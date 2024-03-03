import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID

from .utils import setup_networking


@mock_aws
def test_describe_autoscaling_groups_filter_by_tag_key():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_auto_scaling_groups(
        Filters=[{"Name": "tag-key", "Values": ["test_key1"]}]
    )
    group = response["AutoScalingGroups"][0]
    tags = group["Tags"]

    assert len(response["AutoScalingGroups"]) == 1
    assert response["AutoScalingGroups"][0]["AutoScalingGroupName"] == "test_asg1"
    assert {
        "Key": "test_key1",
        "PropagateAtLaunch": False,
        "ResourceId": "test_asg1",
        "ResourceType": "auto-scaling-group",
        "Value": "test_value1",
    } in tags


@mock_aws
def test_describe_autoscaling_groups_filter_by_tag_value():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_auto_scaling_groups(
        Filters=[{"Name": "tag-value", "Values": ["test_value1"]}]
    )
    group = response["AutoScalingGroups"][0]
    tags = group["Tags"]

    assert len(response["AutoScalingGroups"]) == 1
    assert response["AutoScalingGroups"][0]["AutoScalingGroupName"] == "test_asg1"
    assert {
        "Key": "test_key1",
        "PropagateAtLaunch": False,
        "ResourceId": "test_asg1",
        "ResourceType": "auto-scaling-group",
        "Value": "test_value1",
    } in tags


@mock_aws
def test_describe_autoscaling_groups_filter_by_tag_key_value():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_auto_scaling_groups(
        Filters=[{"Name": "tag:test_key1", "Values": ["test_value1"]}]
    )
    group = response["AutoScalingGroups"][0]
    tags = group["Tags"]

    assert len(response["AutoScalingGroups"]) == 1
    assert response["AutoScalingGroups"][0]["AutoScalingGroupName"] == "test_asg1"
    assert {
        "Key": "test_key1",
        "PropagateAtLaunch": False,
        "ResourceId": "test_asg1",
        "ResourceType": "auto-scaling-group",
        "Value": "test_value1",
    } in tags


@mock_aws
def test_describe_autoscaling_groups_no_filter():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_auto_scaling_groups()

    assert len(response["AutoScalingGroups"]) == 2
    assert response["AutoScalingGroups"][0]["AutoScalingGroupName"] == "test_asg1"
    assert response["AutoScalingGroups"][1]["AutoScalingGroupName"] == "test_asg2"


def create_asgs(client, subnet):
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg1",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {"Key": "test_key1", "Value": "test_value1"},
            {"Key": "test_key2", "Value": "test_value2"},
        ],
        VPCZoneIdentifier=subnet,
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg2",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=subnet,
    )
