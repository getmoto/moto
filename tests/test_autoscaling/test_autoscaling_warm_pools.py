from unittest import TestCase

import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID

from .utils import setup_networking


@mock_aws
class TestAutoScalingGroup(TestCase):
    def setUp(self) -> None:
        self.mocked_networking = setup_networking()
        self.as_client = boto3.client("autoscaling", region_name="us-east-1")
        self.ec2_client = boto3.client("ec2", region_name="us-east-1")
        self.lc_name = "tester_config"
        self.asg_name = "asg_test"
        self.ec2_client.create_launch_template(
            LaunchTemplateName="launchie",
            LaunchTemplateData={"ImageId": EXAMPLE_AMI_ID},
        )["LaunchTemplate"]
        input_policy = {
            "LaunchTemplate": {
                "LaunchTemplateSpecification": {
                    "LaunchTemplateName": "launchie",
                    "Version": "$DEFAULT",
                }
            }
        }

        self.as_client.create_auto_scaling_group(
            MixedInstancesPolicy=input_policy,
            AutoScalingGroupName=self.asg_name,
            MinSize=2,
            MaxSize=2,
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

    def test_put_warm_pool(self):
        self.as_client.put_warm_pool(
            AutoScalingGroupName=self.asg_name,
            MaxGroupPreparedCapacity=42,
            MinSize=7,
            PoolState="Stopped",
            InstanceReusePolicy={"ReuseOnScaleIn": True},
        )

        pool = self.as_client.describe_warm_pool(AutoScalingGroupName=self.asg_name)
        assert pool["WarmPoolConfiguration"] == {
            "MaxGroupPreparedCapacity": 42,
            "MinSize": 7,
            "PoolState": "Stopped",
            "InstanceReusePolicy": {"ReuseOnScaleIn": True},
        }

        group = self.as_client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
        assert group["WarmPoolConfiguration"] == {
            "InstanceReusePolicy": {"ReuseOnScaleIn": True},
            "MaxGroupPreparedCapacity": 42,
            "MinSize": 7,
            "PoolState": "Stopped",
        }

    def test_describe_pool_not_created(self):
        pool = self.as_client.describe_warm_pool(AutoScalingGroupName=self.asg_name)
        assert "WarmPoolConfiguration" not in pool
        assert pool["Instances"] == []

    def test_delete_pool(self):
        self.as_client.put_warm_pool(
            AutoScalingGroupName=self.asg_name,
            MinSize=2,
        )
        self.as_client.delete_warm_pool(AutoScalingGroupName=self.asg_name)
        pool = self.as_client.describe_warm_pool(AutoScalingGroupName=self.asg_name)
        assert "WarmPoolConfiguration" not in pool
        assert pool["Instances"] == []

    def test_describe_pool_with_defaults(self):
        self.as_client.put_warm_pool(
            AutoScalingGroupName=self.asg_name,
            MinSize=2,
        )
        pool = self.as_client.describe_warm_pool(AutoScalingGroupName=self.asg_name)
        assert pool["WarmPoolConfiguration"] == {"MinSize": 2, "PoolState": "Stopped"}
        assert pool["Instances"] == []
