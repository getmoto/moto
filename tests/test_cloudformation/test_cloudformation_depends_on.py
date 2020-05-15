import boto3
from moto import mock_cloudformation, mock_ec2
import json

# @pytest.fixture(scope="module")
@mock_ec2
def make_subnet():
    ec2 = boto3.resource("ec2")
    default_vpc = list(ec2.vpcs.all())[0]
    ec2.create_subnet(
        VpcId=default_vpc.id, CidrBlock="172.31.48.0/20", AvailabilityZone="us-east-1a"
    )


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
@mock_ec2
def test_create_stack_with_depends_on():
    make_subnet()
    boto3.client("cloudformation").create_stack(
        StackName="depends_on_test", TemplateBody=depends_on_template_json
    )
