import json

import boto3

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID

depends_on_template_list = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "ECSCluster": {
            "Type": "AWS::ECS::Cluster",
            "Properties": {"ClusterName": "test-cluster"},
        },
        "AutoScalingGroup": {
            "Type": "AWS::AutoScaling::AutoScalingGroup",
            "Properties": {
                "AutoScalingGroupName": "test-scaling-group",
                "DesiredCapacity": 1,
                "MinSize": 1,
                "MaxSize": 50,
                "LaunchConfigurationName": "test-launch-config",
                "AvailabilityZones": ["us-east-1a"],
            },
            "DependsOn": ["ECSCluster", "LaunchConfig"],
        },
        "LaunchConfig": {
            "Type": "AWS::AutoScaling::LaunchConfiguration",
            "Properties": {
                "LaunchConfigurationName": "test-launch-config",
                "ImageId": EXAMPLE_AMI_ID,
                "InstanceType": "t2.medium",
            },
        },
    },
}

depends_on_template_string = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Resources": {
        "AutoScalingGroup": {
            "Type": "AWS::AutoScaling::AutoScalingGroup",
            "Properties": {
                "AutoScalingGroupName": "test-scaling-group",
                "DesiredCapacity": 1,
                "MinSize": 1,
                "MaxSize": 50,
                "LaunchConfigurationName": "test-launch-config",
                "AvailabilityZones": ["us-east-1a"],
            },
            "DependsOn": "LaunchConfig",
        },
        "LaunchConfig": {
            "Type": "AWS::AutoScaling::LaunchConfiguration",
            "Properties": {
                "LaunchConfigurationName": "test-launch-config",
                "ImageId": EXAMPLE_AMI_ID,
                "InstanceType": "t2.medium",
            },
        },
    },
}


def make_chained_depends_on_template():
    depends_on_template_linked_dependencies = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {
            "Bucket1": {
                "Type": "AWS::S3::Bucket",
                "Properties": {"BucketName": "test-bucket-0-us-east-1"},
            },
        },
    }

    for i in range(1, 10):
        depends_on_template_linked_dependencies["Resources"]["Bucket" + str(i)] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {"BucketName": "test-bucket-" + str(i) + "-us-east-1"},
            "DependsOn": ["Bucket" + str(i - 1)],
        }

    return json.dumps(depends_on_template_linked_dependencies)


depends_on_template_list_json = json.dumps(depends_on_template_list)
depends_on_template_string_json = json.dumps(depends_on_template_string)


@mock_aws
def test_create_stack_with_depends_on():
    boto3.client("cloudformation", region_name="us-east-1").create_stack(
        StackName="depends_on_test", TemplateBody=depends_on_template_list_json
    )

    autoscaling = boto3.client("autoscaling", region_name="us-east-1")
    autoscaling_group = autoscaling.describe_auto_scaling_groups()["AutoScalingGroups"][
        0
    ]
    assert autoscaling_group["AutoScalingGroupName"] == "test-scaling-group"
    assert autoscaling_group["DesiredCapacity"] == 1
    assert autoscaling_group["MinSize"] == 1
    assert autoscaling_group["MaxSize"] == 50
    assert autoscaling_group["AvailabilityZones"] == ["us-east-1a"]

    launch_configuration = autoscaling.describe_launch_configurations()[
        "LaunchConfigurations"
    ][0]
    assert launch_configuration["LaunchConfigurationName"] == "test-launch-config"

    ecs = boto3.client("ecs", region_name="us-east-1")
    cluster_arn = ecs.list_clusters()["clusterArns"][0]
    assert cluster_arn == f"arn:aws:ecs:us-east-1:{ACCOUNT_ID}:cluster/test-cluster"


@mock_aws
def test_create_stack_with_depends_on_string():
    boto3.client("cloudformation", region_name="us-east-1").create_stack(
        StackName="depends_on_string_test", TemplateBody=depends_on_template_string_json
    )

    autoscaling = boto3.client("autoscaling", region_name="us-east-1")
    autoscaling_group = autoscaling.describe_auto_scaling_groups()["AutoScalingGroups"][
        0
    ]
    assert autoscaling_group["AutoScalingGroupName"] == "test-scaling-group"
    assert autoscaling_group["DesiredCapacity"] == 1
    assert autoscaling_group["MinSize"] == 1
    assert autoscaling_group["MaxSize"] == 50
    assert autoscaling_group["AvailabilityZones"] == ["us-east-1a"]

    launch_configuration = autoscaling.describe_launch_configurations()[
        "LaunchConfigurations"
    ][0]
    assert launch_configuration["LaunchConfigurationName"] == "test-launch-config"


@mock_aws
def test_create_chained_depends_on_stack():
    boto3.client("cloudformation", region_name="us-east-1").create_stack(
        StackName="linked_depends_on_test",
        TemplateBody=make_chained_depends_on_template(),
    )

    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_response = s3.list_buckets()["Buckets"]

    assert sorted([bucket["Name"] for bucket in bucket_response]) == [
        "test-bucket-" + str(i) + "-us-east-1" for i in range(1, 10)
    ]
