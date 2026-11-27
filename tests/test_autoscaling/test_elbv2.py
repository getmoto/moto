import unittest
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from tests import EXAMPLE_AMI_ID

from .utils import setup_networking


@pytest.mark.parametrize("capacity", [0, 1])
@pytest.mark.parametrize("deleted_count", [0, 1, 2])
@mock_aws
def test_delete_group_with_deleted_target_groups(capacity, deleted_count):
    networking = setup_networking()
    autoscaling = boto3.client("autoscaling", region_name="us-east-1")
    elbv2 = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.client("ec2", region_name="us-east-1")
    target_groups = [
        elbv2.create_target_group(
            Name=name, Protocol="HTTP", Port=80, VpcId=networking["vpc"]
        )["TargetGroups"][0]["TargetGroupArn"]
        for name in ["first", "second"]
    ]
    autoscaling.create_launch_configuration(
        LaunchConfigurationName="lc",
        ImageId=EXAMPLE_AMI_ID,
        InstanceType="t2.micro",
    )
    autoscaling.create_auto_scaling_group(
        AutoScalingGroupName="asg",
        LaunchConfigurationName="lc",
        MinSize=0,
        MaxSize=1,
        DesiredCapacity=capacity,
        VPCZoneIdentifier=networking["subnet1"],
        TargetGroupARNs=target_groups,
    )
    group = autoscaling.describe_auto_scaling_groups()["AutoScalingGroups"][0]
    instance_ids = [instance["InstanceId"] for instance in group["Instances"]]
    # A target group can be deleted while it is still attached to an ASG.
    for arn in target_groups[:deleted_count]:
        elbv2.delete_target_group(TargetGroupArn=arn)

    autoscaling.delete_auto_scaling_group(
        AutoScalingGroupName="asg", ForceDelete=bool(capacity)
    )

    assert autoscaling.describe_auto_scaling_groups()["AutoScalingGroups"] == []
    if instance_ids:
        instances = ec2.describe_instances(InstanceIds=instance_ids)
        assert all(
            instance["State"]["Name"] == "terminated"
            for reservation in instances["Reservations"]
            for instance in reservation["Instances"]
        )
    assert {
        group["TargetGroupArn"]
        for group in elbv2.describe_target_groups()["TargetGroups"]
    } == set(target_groups[deleted_count:])
    # Missing target groups must still be reported by ELBv2 itself.
    for arn in target_groups[:deleted_count]:
        with pytest.raises(ClientError) as error:
            elbv2.describe_target_groups(TargetGroupArns=[arn])
        assert error.value.response["Error"]["Code"] == "TargetGroupNotFound"


@mock_aws
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

    def test_failed_delete_preserves_target_group_attachments(self):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        group = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )["AutoScalingGroups"][0]
        instance_id = group["Instances"][0]["InstanceId"]
        ec2.modify_instance_attribute(
            InstanceId=instance_id, DisableApiTermination={"Value": True}
        )
        self.elbv2_client.delete_target_group(TargetGroupArn=self.target_group_arn)

        with pytest.raises(ClientError) as error:
            self.as_client.delete_auto_scaling_group(
                AutoScalingGroupName=self.asg_name, ForceDelete=True
            )
        assert error.value.response["Error"]["Code"] == "OperationNotPermitted"
        group = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )["AutoScalingGroups"][0]
        assert group["TargetGroupARNs"] == [self.target_group_arn]

        ec2.modify_instance_attribute(
            InstanceId=instance_id, DisableApiTermination={"Value": False}
        )
        self.as_client.delete_auto_scaling_group(
            AutoScalingGroupName=self.asg_name, ForceDelete=True
        )
        assert self.as_client.describe_auto_scaling_groups()["AutoScalingGroups"] == []

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
