from __future__ import unicode_literals
import boto3
import sure  # noqa

from moto import mock_autoscaling


@mock_autoscaling
def test_create_autoscaling_group():
        client = boto3.client('autoscaling', region_name='us-east-1')
        _ = client.create_launch_configuration(
            LaunchConfigurationName='test_launch_configuration'
        )
        response = client.create_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            LaunchConfigurationName='test_launch_configuration',
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5
        )
        response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)


@mock_autoscaling
def test_describe_autoscaling_groups():
        client = boto3.client('autoscaling', region_name='us-east-1')
        _ = client.create_launch_configuration(
            LaunchConfigurationName='test_launch_configuration'
        )
        _ = client.create_auto_scaling_group(
            AutoScalingGroupName='test_asg',
            LaunchConfigurationName='test_launch_configuration',
            MinSize=0,
            MaxSize=20,
            DesiredCapacity=5
        )
        response = client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test_asg"]
        )
        response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)
        response['AutoScalingGroups'][0]['AutoScalingGroupName'].should.equal('test_asg')
