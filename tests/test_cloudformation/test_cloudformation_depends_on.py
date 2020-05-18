import boto3
from moto import mock_cloudformation, mock_ecs, mock_autoscaling, mock_s3
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
        depends_on_template_linked_dependencies["Resources"][f"Bucket{i}"] = {
            "Type": "AWS::S3::Bucket",
            "Properties": {"BucketName": f"test-bucket-{i}-us-east-1"},
            "DependsOn": [f"Bucket{i - 1}"],
        }

    return json.dumps(depends_on_template_linked_dependencies)


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


@mock_cloudformation
@mock_s3
def test_create_chained_depends_on_stack():
    boto3.client("cloudformation", region_name="us-east-1").create_stack(
        StackName="linked_depends_on_test",
        TemplateBody=make_chained_depends_on_template(),
    )

    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_response = s3.list_buckets()["Buckets"]

    assert [bucket["Name"] for bucket in bucket_response] == [
        f"test-bucket-{i}-us-east-1" for i in range(1, 10)
    ]
