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
            "AutoScalingGroupName": "test-scaling-group",
            "Properties": {
                "AvailabilityZones": ["us-east-1"]
            },
            "DependsOn": ["ECSCluster", "LaunchConfig"],
        },
        "LaunchConfig": {
            "Type": "AWS::AutoScaling::LaunchConfiguration",
            "LaunchConfigurationName": "test-launch-config",
            "Properties": {

            }
        }
    },
}

depends_on_template_json = json.dumps(depends_on_template)

@mock_cloudformation
def test_create_stack_with_depends_on():
    boto3.client("cloudformation").create_stack(StackName="depends_on_test",
                                                TemplateBody=depends_on_template_json)

if __name__ == '__main__':
    test_create_stack_with_depends_on()
