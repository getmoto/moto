import boto3
import unittest
from moto import mock_autoscaling, mock_elbv2
from tests import EXAMPLE_AMI_ID
from uuid import uuid4
from .utils import setup_networking


@mock_elbv2
@mock_autoscaling
class TestAutoscalignELBv2(unittest.TestCase):
    def setUp(self) -> None:
        self.mocked_networking = setup_networking()
        self.instance_count = 2
        self.as_client = boto3.client("autoscaling", region_name="us-east-1")
        self.elbv2_client = boto3.client("elbv2", region_name="us-east-1")

        self.target_name = str(uuid4())[0:6]
        self.lc_name = str(uuid4())[0:6]
        self.asg_name = str(uuid4())[0:6]
        response = self.elbv2_client.create_target_group(
            Name=self.target_name,
            Protocol="HTTP",
            Port=8080,
            VpcId=self.mocked_networking["vpc"],
            HealthCheckProtocol="HTTP",
            HealthCheckPort="8080",
            HealthCheckPath="/",
            HealthCheckIntervalSeconds=5,
            HealthCheckTimeoutSeconds=3,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={"HttpCode": "200"},
        )
        self.target_group_arn = response["TargetGroups"][0]["TargetGroupArn"]

        self.as_client.create_launch_configuration(
            LaunchConfigurationName=self.lc_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            MinSize=0,
            MaxSize=self.instance_count,
            DesiredCapacity=self.instance_count,
            TargetGroupARNs=[self.target_group_arn],
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

        response = self.as_client.describe_load_balancer_target_groups(
            AutoScalingGroupName=self.asg_name
        )
        assert len(list(response["LoadBalancerTargetGroups"])) == 1

        response = self.elbv2_client.describe_target_health(
            TargetGroupArn=self.target_group_arn
        )
        assert len(list(response["TargetHealthDescriptions"])) == self.instance_count

    def test_attach_detach_target_groups(self):
        # create asg without attaching to target group
        asg_name2 = str(uuid4())
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=asg_name2,
            LaunchConfigurationName=self.lc_name,
            MinSize=0,
            MaxSize=self.instance_count,
            DesiredCapacity=self.instance_count,
            VPCZoneIdentifier=self.mocked_networking["subnet2"],
        )

        self.as_client.attach_load_balancer_target_groups(
            AutoScalingGroupName=asg_name2, TargetGroupARNs=[self.target_group_arn]
        )

        response = self.elbv2_client.describe_target_health(
            TargetGroupArn=self.target_group_arn
        )
        assert (
            len(list(response["TargetHealthDescriptions"])) == self.instance_count * 2
        )

        response = self.as_client.detach_load_balancer_target_groups(
            AutoScalingGroupName=asg_name2, TargetGroupARNs=[self.target_group_arn]
        )
        response = self.elbv2_client.describe_target_health(
            TargetGroupArn=self.target_group_arn
        )
        assert len(list(response["TargetHealthDescriptions"])) == self.instance_count

    def test_detach_all_target_groups(self):
        response = self.as_client.detach_load_balancer_target_groups(
            AutoScalingGroupName=self.asg_name, TargetGroupARNs=[self.target_group_arn]
        )

        response = self.elbv2_client.describe_target_health(
            TargetGroupArn=self.target_group_arn
        )
        assert len(list(response["TargetHealthDescriptions"])) == 0
        response = self.as_client.describe_load_balancer_target_groups(
            AutoScalingGroupName=self.asg_name
        )
        assert len(list(response["LoadBalancerTargetGroups"])) == 0
