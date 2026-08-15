import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID

from .utils import setup_networking


def _create_tagged_asgs(client, subnet):
    client.create_launch_configuration(
        LaunchConfigurationName="rgtapi-lc",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.medium",
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="rgtapi-asg-1",
        LaunchConfigurationName="rgtapi-lc",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=0,
        Tags=[
            {"Key": "env", "Value": "prod", "PropagateAtLaunch": True},
            {"Key": "team", "Value": "platform", "PropagateAtLaunch": False},
        ],
        VPCZoneIdentifier=subnet,
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="rgtapi-asg-2",
        LaunchConfigurationName="rgtapi-lc",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=0,
        Tags=[
            {"Key": "env", "Value": "dev", "PropagateAtLaunch": True},
        ],
        VPCZoneIdentifier=subnet,
    )
    client.create_auto_scaling_group(
        AutoScalingGroupName="rgtapi-asg-untagged",
        LaunchConfigurationName="rgtapi-lc",
        MinSize=0,
        MaxSize=2,
        DesiredCapacity=0,
        VPCZoneIdentifier=subnet,
    )


@mock_aws
def test_rgtapi_tag_resources_updates_autoscaling_group():
    subnet = setup_networking()["subnet1"]
    asg = boto3.client("autoscaling", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_asgs(asg, subnet)

    resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=["rgtapi-asg-1"])
    arn = resp["AutoScalingGroups"][0]["AutoScalingGroupARN"]

    resp = rtapi.tag_resources(
        ResourceARNList=[arn], Tags={"owner": "dataops", "env": "staging"}
    )
    assert resp.get("FailedResourcesMap", {}) == {}

    resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=["rgtapi-asg-1"])
    tags = resp["AutoScalingGroups"][0]["Tags"]
    by_key = {t["Key"]: t for t in tags}
    assert by_key["owner"]["Value"] == "dataops"
    # Existing tag should be updated in place.
    assert by_key["env"]["Value"] == "staging"
    # Pre-existing tags survive.
    assert by_key["team"]["Value"] == "platform"


@mock_aws
def test_rgtapi_untag_resources_removes_autoscaling_tags():
    subnet = setup_networking()["subnet1"]
    asg = boto3.client("autoscaling", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    _create_tagged_asgs(asg, subnet)

    resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=["rgtapi-asg-1"])
    arn = resp["AutoScalingGroups"][0]["AutoScalingGroupARN"]

    rtapi.untag_resources(ResourceARNList=[arn], TagKeys=["env"])

    resp = asg.describe_auto_scaling_groups(AutoScalingGroupNames=["rgtapi-asg-1"])
    tags = resp["AutoScalingGroups"][0]["Tags"]
    assert "env" not in {t["Key"] for t in tags}
    assert "team" in {t["Key"] for t in tags}
