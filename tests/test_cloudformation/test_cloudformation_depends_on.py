import boto3
from moto import mock_cloudformation
import json

depends_on_template = {
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

depends_on_template_json = json.dumps(depends_on_template)


@mock_cloudformation
def test_create_stack_with_depends_on():
    boto3.client("cloudformation", region_name="us-east-1").create_stack(
        StackName="depends_on_test", TemplateBody=depends_on_template_json
    )
