from __future__ import unicode_literals
import boto3

import sure  # noqa
from moto import mock_autoscaling, mock_ec2, mock_elbv2

from utils import setup_networking


@mock_elbv2
@mock_autoscaling
def test_attach_detach_target_groups():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2
    client = boto3.client("autoscaling", region_name="us-east-1")
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")

    response = elbv2_client.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=mocked_networking["vpc"],
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )

    # create asg, attach to target group on create
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        TargetGroupARNs=[target_group_arn],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )
    # create asg without attaching to target group
    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg2",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        VPCZoneIdentifier=mocked_networking["subnet2"],
    )

    response = client.describe_load_balancer_target_groups(
        AutoScalingGroupName="test_asg"
    )
    list(response["LoadBalancerTargetGroups"]).should.have.length_of(1)

    response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
    list(response["TargetHealthDescriptions"]).should.have.length_of(INSTANCE_COUNT)

    client.attach_load_balancer_target_groups(
        AutoScalingGroupName="test_asg2", TargetGroupARNs=[target_group_arn]
    )

    response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
    list(response["TargetHealthDescriptions"]).should.have.length_of(INSTANCE_COUNT * 2)

    response = client.detach_load_balancer_target_groups(
        AutoScalingGroupName="test_asg2", TargetGroupARNs=[target_group_arn]
    )
    response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
    list(response["TargetHealthDescriptions"]).should.have.length_of(INSTANCE_COUNT)


@mock_elbv2
@mock_autoscaling
def test_detach_all_target_groups():
    mocked_networking = setup_networking()
    INSTANCE_COUNT = 2
    client = boto3.client("autoscaling", region_name="us-east-1")
    elbv2_client = boto3.client("elbv2", region_name="us-east-1")

    response = elbv2_client.create_target_group(
        Name="a-target",
        Protocol="HTTP",
        Port=8080,
        VpcId=mocked_networking["vpc"],
        HealthCheckProtocol="HTTP",
        HealthCheckPort="8080",
        HealthCheckPath="/",
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={"HttpCode": "200"},
    )
    target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]

    client.create_launch_configuration(
        LaunchConfigurationName="test_launch_configuration"
    )

    client.create_auto_scaling_group(
        AutoScalingGroupName="test_asg",
        LaunchConfigurationName="test_launch_configuration",
        MinSize=0,
        MaxSize=INSTANCE_COUNT,
        DesiredCapacity=INSTANCE_COUNT,
        TargetGroupARNs=[target_group_arn],
        VPCZoneIdentifier=mocked_networking["subnet1"],
    )

    response = client.describe_load_balancer_target_groups(
        AutoScalingGroupName="test_asg"
    )
    list(response["LoadBalancerTargetGroups"]).should.have.length_of(1)

    response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
    list(response["TargetHealthDescriptions"]).should.have.length_of(INSTANCE_COUNT)

    response = client.detach_load_balancer_target_groups(
        AutoScalingGroupName="test_asg", TargetGroupARNs=[target_group_arn]
    )

    response = elbv2_client.describe_target_health(TargetGroupArn=target_group_arn)
    list(response["TargetHealthDescriptions"]).should.have.length_of(0)
    response = client.describe_load_balancer_target_groups(
        AutoScalingGroupName="test_asg"
    )
    list(response["LoadBalancerTargetGroups"]).should.have.length_of(0)
