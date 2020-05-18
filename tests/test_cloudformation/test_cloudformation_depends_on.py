import boto3
from moto import mock_cloudformation, mock_ecs, mock_autoscaling
import json

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
            "Properties": {"LaunchConfigurationName": "test-launch-config",},
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
            "Properties": {"LaunchConfigurationName": "test-launch-config",},
        },
    },
}


depends_on_template_list_json = json.dumps(depends_on_template_list)
depends_on_template_string_json = json.dumps(depends_on_template_string)


@mock_cloudformation
@mock_autoscaling
@mock_ecs
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
    assert cluster_arn == "arn:aws:ecs:us-east-1:012345678910:cluster/test-cluster"


@mock_cloudformation
@mock_autoscaling
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
