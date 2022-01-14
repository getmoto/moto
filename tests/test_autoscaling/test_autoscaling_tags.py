import boto3

from moto import mock_autoscaling, mock_ec2

from .utils import setup_networking
from tests import EXAMPLE_AMI_ID


@mock_autoscaling
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
    response["AutoScalingGroups"][0]["Tags"].should.have.length_of(2)


@mock_autoscaling
@mock_ec2
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
    tags.should.contain(tag_to_keep)
    tags.should_not.contain(tag_to_delete)


@mock_autoscaling
def test_describe_tags_without_resources():
    client = boto3.client("autoscaling", region_name="us-east-2")
    resp = client.describe_tags()
    resp.should.have.key("Tags").equals([])
    resp.shouldnt.have.key("NextToken")


@mock_autoscaling
def test_describe_tags_no_filter():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_tags()
    response.should.have.key("Tags").length_of(4)
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key",
            "Value": "updated_test_value",
            "PropagateAtLaunch": True,
        }
    )
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key2",
            "Value": "test_value2",
            "PropagateAtLaunch": False,
        }
    )
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg2",
            "ResourceType": "auto-scaling-group",
            "Key": "asg2tag1",
            "Value": "val",
            "PropagateAtLaunch": False,
        }
    )
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg2",
            "ResourceType": "auto-scaling-group",
            "Key": "asg2tag2",
            "Value": "diff",
            "PropagateAtLaunch": False,
        }
    )


@mock_autoscaling
def test_describe_tags_filter_by_name():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_tags(
        Filters=[{"Name": "auto-scaling-group", "Values": ["test_asg"]}]
    )
    response.should.have.key("Tags").length_of(2)
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key",
            "Value": "updated_test_value",
            "PropagateAtLaunch": True,
        }
    )
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key2",
            "Value": "test_value2",
            "PropagateAtLaunch": False,
        }
    )

    response = client.describe_tags(
        Filters=[{"Name": "auto-scaling-group", "Values": ["test_asg", "test_asg2"]}]
    )
    response.should.have.key("Tags").length_of(4)
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key",
            "Value": "updated_test_value",
            "PropagateAtLaunch": True,
        }
    )
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key2",
            "Value": "test_value2",
            "PropagateAtLaunch": False,
        }
    )
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg2",
            "ResourceType": "auto-scaling-group",
            "Key": "asg2tag1",
            "Value": "val",
            "PropagateAtLaunch": False,
        }
    )
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg2",
            "ResourceType": "auto-scaling-group",
            "Key": "asg2tag2",
            "Value": "diff",
            "PropagateAtLaunch": False,
        }
    )


@mock_autoscaling
def test_describe_tags_filter_by_propgateatlaunch():
    subnet = setup_networking()["subnet1"]
    client = boto3.client("autoscaling", region_name="us-east-1")
    create_asgs(client, subnet)

    response = client.describe_tags(
        Filters=[{"Name": "propagate-at-launch", "Values": ["True"]}]
    )
    response.should.have.key("Tags").length_of(1)
    response["Tags"].should.contain(
        {
            "ResourceId": "test_asg",
            "ResourceType": "auto-scaling-group",
            "Key": "test_key",
            "Value": "updated_test_value",
            "PropagateAtLaunch": True,
        }
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
