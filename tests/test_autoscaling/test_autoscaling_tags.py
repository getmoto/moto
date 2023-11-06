import copy

import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID

from .utils import setup_networking


@mock_aws
def test_autoscaling_tags_update():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    _ = client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "test_value",
                "PropagateAtLaunch": True,
            }
        ],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.create_or_update_tags(
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "updated_test_value",
                "PropagateAtLaunch": True,
            },
            {
                "ResourceId": "test_asg",
                "Key": "test_key2",
                "Value": "test_value2",
                "PropagateAtLaunch": False,
            },
        ]
    )

    response = client.describe_auto_scaling_groups(AutoScalingGroupNames=["test_asg"])
    assert len(response["AutoScalingGroups"][0]["Tags"]) == 2


@mock_aws
def test_delete_tags_by_key():
    mocked_networking = setup_networking()
    client = boto3.client("autoscaling", region_name="us-east-1")
    client.create_launch_configuration(
        LaunchConfigurationName="TestLC",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    tag_to_delete = {
        "ResourceId": "tag_test_asg",
        "ResourceType": "auto-scaling-group",
        "PropagateAtLaunch": True,
        "Key": "TestDeleteTagKey1",
        "Value": "TestTagValue1",
    }
    tag_to_keep = {
        "ResourceId": "tag_test_asg",
        "ResourceType": "auto-scaling-group",
        "PropagateAtLaunch": True,
        "Key": "TestTagKey1",
        "Value": "TestTagValue1",
    }
    client.create_auto_scaling_group(
        AutoScalingGroupName="tag_test_asg",
        MinSize=1,
        MaxSize=2,
        LaunchConfigurationName="TestLC",
        Tags=[tag_to_delete, tag_to_keep],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    client.delete_tags(
        Tags=[
            {
                "ResourceId": "tag_test_asg",
                "ResourceType": "auto-scaling-group",
                "PropagateAtLaunch": True,
                "Key": "TestDeleteTagKey1",
            }
        ]
    )
    response = client.describe_auto_scaling_groups(
        AutoScalingGroupNames=["tag_test_asg"]
    )
    group = response["AutoScalingGroups"][0]
    tags = group["Tags"]
    assert tag_to_keep in tags
    assert tag_to_delete not in tags


@mock_aws
def test_describe_tags_without_resources():
    client = boto3.client("autoscaling", region_name="us-east-2")
    resp = client.describe_tags()
    assert resp["Tags"] == []
    assert "NextToken" not in resp


@mock_aws
def test_describe_tags_no_filter():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_tags()
    len(response["Tags"]) == 4
    assert {
        "ResourceId": "test_asg",
        "ResourceType": "auto-scaling-group",
        "Key": "test_key",
        "Value": "updated_test_value",
        "PropagateAtLaunch": True,
    } in response["Tags"]
    assert {
        "ResourceId": "test_asg",
        "ResourceType": "auto-scaling-group",
        "Key": "test_key2",
        "Value": "test_value2",
        "PropagateAtLaunch": False,
    } in response["Tags"]
    assert {
        "ResourceId": "test_asg2",
        "ResourceType": "auto-scaling-group",
        "Key": "asg2tag1",
        "Value": "val",
        "PropagateAtLaunch": False,
    } in response["Tags"]
    assert {
        "ResourceId": "test_asg2",
        "ResourceType": "auto-scaling-group",
        "Key": "asg2tag2",
        "Value": "diff",
        "PropagateAtLaunch": False,
    } in response["Tags"]


@mock_aws
def test_describe_tags_filter_by_name():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_tags(
        Filters=[{"Name": "auto-scaling-group", "Values": ["test_asg"]}]
    )
    assert len(response["Tags"]) == 2
    assert {
        "ResourceId": "test_asg",
        "ResourceType": "auto-scaling-group",
        "Key": "test_key",
        "Value": "updated_test_value",
        "PropagateAtLaunch": True,
    } in response["Tags"]
    assert {
        "ResourceId": "test_asg",
        "ResourceType": "auto-scaling-group",
        "Key": "test_key2",
        "Value": "test_value2",
        "PropagateAtLaunch": False,
    } in response["Tags"]

    response = client.describe_tags(
        Filters=[{"Name": "auto-scaling-group", "Values": ["test_asg", "test_asg2"]}]
    )
    assert len(response["Tags"]) == 4
    assert {
        "ResourceId": "test_asg",
        "ResourceType": "auto-scaling-group",
        "Key": "test_key",
        "Value": "updated_test_value",
        "PropagateAtLaunch": True,
    } in response["Tags"]
    assert {
        "ResourceId": "test_asg",
        "ResourceType": "auto-scaling-group",
        "Key": "test_key2",
        "Value": "test_value2",
        "PropagateAtLaunch": False,
    } in response["Tags"]
    assert {
        "ResourceId": "test_asg2",
        "ResourceType": "auto-scaling-group",
        "Key": "asg2tag1",
        "Value": "val",
        "PropagateAtLaunch": False,
    } in response["Tags"]
    assert {
        "ResourceId": "test_asg2",
        "ResourceType": "auto-scaling-group",
        "Key": "asg2tag2",
        "Value": "diff",
        "PropagateAtLaunch": False,
    } in response["Tags"]


@mock_aws
def test_describe_tags_filter_by_propgateatlaunch():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_tags(
        Filters=[{"Name": "propagate-at-launch", "Values": ["True"]}]
    )
    len(response["Tags"]) == 1
    assert response["Tags"] == [
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key",
            "Value": "updated_test_value",
            "PropagateAtLaunch": True,
        }
    ]


@mock_aws
def test_describe_tags_filter_by_key_or_value():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    tags = client.describe_tags(Filters=[{"Name": "key", "Values": ["test_key"]}])[
        "Tags"
    ]
    assert tags == [
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key",
            "Value": "updated_test_value",
            "PropagateAtLaunch": True,
        }
    ]

    tags = client.describe_tags(Filters=[{"Name": "value", "Values": ["test_value2"]}])[
        "Tags"
    ]
    assert tags == [
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key2",
            "Value": "test_value2",
            "PropagateAtLaunch": False,
        }
    ]


@mock_aws
def test_create_20_tags_auto_scaling_group():
    """test to verify that the tag-members are sorted correctly, and there is no regression for
    https://github.com/getmoto/moto/issues/6033
    """
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    original = {
        "ResourceId": "test_asg",
        "PropagateAtLaunch": True,
    }
    tags = []
    for i in range(0, 20):
        cp = copy.deepcopy(original)
        cp["Key"] = f"test_key{i}"
        cp["Value"] = f"random-value-{i}"
        tags.append(cp)
    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=tags,
        VPCZoneIdentifier=subnet,
    )


def create_asgs(client, subnet):
    _ = client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        VPCZoneIdentifier=subnet,
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg2",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=20,
        DesiredCapacity=5,
        Tags=[
            {"Key": "asg2tag1", "Value": "val"},
            {"Key": "asg2tag2", "Value": "diff"},
        ],
        VPCZoneIdentifier=subnet,
    )
    client.create_or_update_tags(
        Tags=[
            {
                "ResourceId": "test_asg",
                "Key": "test_key",
                "Value": "updated_test_value",
                "PropagateAtLaunch": True,
            },
            {
                "ResourceId": "test_asg",
                "Key": "test_key2",
                "Value": "test_value2",
                "PropagateAtLaunch": False,
            },
        ]
    )
