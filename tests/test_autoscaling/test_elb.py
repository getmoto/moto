from unittest import TestCase
from uuid import uuid4

import boto3

from moto import mock_aws
from tests import EXAMPLE_AMI_ID

from .utils import setup_networking


@mock_aws
class TestAutoScalingELB(TestCase):
    def setUp(self):
        self.mocked_networking = setup_networking()
        self.instance_count = 2
        self.elb_client = boto3.client("elb", region_name="us-east-1")
        self.as_client = boto3.client("autoscaling", region_name="us-east-1")
        self.lb_name = str(uuid4())
        self.asg_name = str(uuid4())
        self.lc_name = str(uuid4())

        self.elb_client.create_load_balancer(
            LoadBalancerName=self.lb_name,
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )
        self.as_client.create_launch_configuration(
            LaunchConfigurationName=self.lc_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )

    def test_describe_load_balancers(self):
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            LoadBalancerNames=[self.lb_name],
            MinSize=0,
            MaxSize=self.instance_count,
            DesiredCapacity=self.instance_count,
            Tags=[
                {
                    "ResourceId": self.asg_name,
                    "Key": "test_key",
                    "Value": "test_value",
                    "PropagateAtLaunch": True,
                }
            ],
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

        response = self.as_client.describe_load_balancers(
            AutoScalingGroupName=self.asg_name
        )
        assert response["ResponseMetadata"]["RequestId"]
        assert len(list(response["LoadBalancers"])) == 1
        assert response["LoadBalancers"][0]["LoadBalancerName"] == self.lb_name

    def test_create_elb_and_autoscaling_group_no_relationship(self):
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            MinSize=0,
            MaxSize=self.instance_count,
            DesiredCapacity=self.instance_count,
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

        # autoscaling group and elb should have no relationship
        response = self.as_client.describe_load_balancers(
            AutoScalingGroupName=self.asg_name
        )
        assert len(list(response["LoadBalancers"])) == 0
        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 0

    def test_attach_load_balancer(self):
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            MinSize=0,
            MaxSize=self.instance_count,
            DesiredCapacity=self.instance_count,
            Tags=[
                {
                    "ResourceId": self.asg_name,
                    "Key": "test_key",
                    "Value": "test_value",
                    "PropagateAtLaunch": True,
                }
            ],
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

        response = self.as_client.attach_load_balancers(
            AutoScalingGroupName=self.asg_name, LoadBalancerNames=[self.lb_name]
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert (
            len(list(response["LoadBalancerDescriptions"][0]["Instances"]))
            == self.instance_count
        )

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(list(response["AutoScalingGroups"][0]["LoadBalancerNames"])) == 1

    def test_detach_load_balancer(self):
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            LoadBalancerNames=[self.lb_name],
            MinSize=0,
            MaxSize=self.instance_count,
            DesiredCapacity=self.instance_count,
            Tags=[
                {
                    "ResourceId": self.asg_name,
                    "Key": "test_key",
                    "Value": "test_value",
                    "PropagateAtLaunch": True,
                }
            ],
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

        response = self.as_client.detach_load_balancers(
            AutoScalingGroupName=self.asg_name, LoadBalancerNames=[self.lb_name]
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 0

        response = self.as_client.describe_load_balancers(
            AutoScalingGroupName=self.asg_name
        )
        assert len(list(response["LoadBalancers"])) == 0

    def test_create_autoscaling_group_within_elb(self):
        # we attach a couple of machines to the load balancer
        # that are not managed by the auto scaling group
        INSTANCE_COUNT_START = 3
        INSTANCE_COUNT_GROUP = 2
        ec2 = boto3.resource("ec2", region_name="us-east-1")
        instances = ec2.create_instances(
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t1.micro",
            MaxCount=INSTANCE_COUNT_START,
            MinCount=INSTANCE_COUNT_START,
            SubnetId=self.mocked_networking["subnet1"],
        )

        instances_ids = [_.id for _ in instances]
        self.elb_client.register_instances_with_load_balancer(
            LoadBalancerName=self.lb_name,
            Instances=[{"InstanceId": id} for id in instances_ids],
        )

        self.as_client.create_launch_configuration(
            LaunchConfigurationName=self.lc_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )

        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            AvailabilityZones=["us-east-1a", "us-east-1b"],
            DefaultCooldown=60,
            DesiredCapacity=INSTANCE_COUNT_GROUP,
            HealthCheckGracePeriod=100,
            HealthCheckType="EC2",
            LaunchConfigurationName=self.lc_name,
            LoadBalancerNames=[self.lb_name],
            MinSize=INSTANCE_COUNT_GROUP,
            MaxSize=INSTANCE_COUNT_GROUP,
            PlacementGroup="test_placement",
            Tags=[
                {
                    "ResourceId": self.asg_name,
                    "ResourceType": "group",
                    "Key": "test_key",
                    "Value": "test_value",
                    "PropagateAtLaunch": True,
                }
            ],
            TerminationPolicies=["OldestInstance", "NewestInstance"],
            VPCZoneIdentifier=f"{self.mocked_networking['subnet1']},{self.mocked_networking['subnet2']}",
        )

        self.as_client.put_scheduled_update_group_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionName="my-scheduled-action",
            StartTime="2022-07-01T00:00:00Z",
            EndTime="2022-09-01T00:00:00Z",
            Recurrence="* * * * *",
            MinSize=5,
            MaxSize=12,
            DesiredCapacity=9,
        )

        resp = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        group = resp["AutoScalingGroups"][0]
        assert group["AutoScalingGroupName"] == self.asg_name
        assert set(group["AvailabilityZones"]) == set(["us-east-1a", "us-east-1b"])
        assert group["DesiredCapacity"] == 2
        assert group["MaxSize"] == INSTANCE_COUNT_GROUP
        assert group["MinSize"] == INSTANCE_COUNT_GROUP
        assert len(group["Instances"]) == INSTANCE_COUNT_GROUP
        assert (
            group["VPCZoneIdentifier"]
            == f"{self.mocked_networking['subnet1']},{self.mocked_networking['subnet2']}"
        )
        assert group["LaunchConfigurationName"] == self.lc_name
        assert group["DefaultCooldown"] == 60
        assert group["HealthCheckGracePeriod"] == 100
        assert group["HealthCheckType"] == "EC2"
        assert group["LoadBalancerNames"] == [self.lb_name]
        assert group["PlacementGroup"] == "test_placement"
        assert list(group["TerminationPolicies"]) == [
            "OldestInstance",
            "NewestInstance",
        ]
        assert len(list(group["Tags"])) == 1
        tag = group["Tags"][0]
        assert tag["ResourceId"] == self.asg_name
        assert tag["Key"] == "test_key"
        assert tag["Value"] == "test_value"
        assert tag["PropagateAtLaunch"] is True

        instances_attached = self.elb_client.describe_instance_health(
            LoadBalancerName=self.lb_name
        )["InstanceStates"]
        assert len(instances_attached) == INSTANCE_COUNT_START + INSTANCE_COUNT_GROUP
        attached_ids = [i["InstanceId"] for i in instances_attached]
        for ec2_instance_id in instances_ids:
            assert ec2_instance_id in attached_ids

        scheduled_actions = self.as_client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        scheduled_action_1 = scheduled_actions["ScheduledUpdateGroupActions"][0]
        assert scheduled_action_1["AutoScalingGroupName"] == self.asg_name
        assert scheduled_action_1["DesiredCapacity"] == 9
        assert scheduled_action_1["MaxSize"] == 12
        assert scheduled_action_1["MinSize"] == 5
        assert "StartTime" in scheduled_action_1
        assert "EndTime" in scheduled_action_1
        assert scheduled_action_1["Recurrence"] == "* * * * *"
        assert scheduled_action_1["ScheduledActionName"] == "my-scheduled-action"


@mock_aws
class TestAutoScalingInstances(TestCase):
    def setUp(self) -> None:
        self.mocked_networking = setup_networking()
        self.as_client = boto3.client("autoscaling", region_name="us-east-1")
        self.elb_client = boto3.client("elb", region_name="us-east-1")

        self.asg_name = str(uuid4())
        self.lb_name = str(uuid4())
        self.lc_name = str(uuid4())
        self.as_client.create_launch_configuration(
            LaunchConfigurationName=self.lc_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )

        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            MinSize=0,
            MaxSize=2,
            DesiredCapacity=2,
            Tags=[
                {
                    "ResourceId": self.asg_name,
                    "Key": "test_key",
                    "Value": "test_value",
                    "PropagateAtLaunch": True,
                }
            ],
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

        self.elb_client.create_load_balancer(
            LoadBalancerName=self.lb_name,
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )

        response = self.as_client.attach_load_balancers(
            AutoScalingGroupName=self.asg_name, LoadBalancerNames=[self.lb_name]
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_detach_one_instance_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_detach = response["AutoScalingGroups"][0]["Instances"][0][
            "InstanceId"
        ]
        instance_to_keep = response["AutoScalingGroups"][0]["Instances"][1][
            "InstanceId"
        ]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.detach_instances(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_detach],
            ShouldDecrementDesiredCapacity=True,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 1
        assert instance_to_detach not in [
            x["InstanceId"] for x in response["AutoScalingGroups"][0]["Instances"]
        ]

        # test to ensure tag has been removed
        response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        assert len(tags) == 1

        # test to ensure tag is present on other instance
        response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        assert len(tags) == 2

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 1
        assert instance_to_detach not in [
            x["InstanceId"]
            for x in response["LoadBalancerDescriptions"][0]["Instances"]
        ]

    def test_detach_one_instance(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_detach = response["AutoScalingGroups"][0]["Instances"][0][
            "InstanceId"
        ]
        instance_to_keep = response["AutoScalingGroups"][0]["Instances"][1][
            "InstanceId"
        ]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.detach_instances(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_detach],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        # test to ensure instance was replaced
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 2

        response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        assert len(tags) == 1

        response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        assert len(tags) == 2

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 2
        assert instance_to_detach not in [
            x["InstanceId"]
            for x in response["LoadBalancerDescriptions"][0]["Instances"]
        ]

    def test_standby_one_instance_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby = response["AutoScalingGroups"][0]["Instances"][0][
            "InstanceId"
        ]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby],
            ShouldDecrementDesiredCapacity=True,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 2
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 1

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        # test to ensure tag has been retained (standby instance is still part of the ASG)
        response = ec2_client.describe_instances(InstanceIds=[instance_to_standby])
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                tags = instance["Tags"]
                assert len(tags) == 2

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(response["LoadBalancerDescriptions"][0]["Instances"]) == 1
        for x in response["LoadBalancerDescriptions"][0]["Instances"]:
            assert x["InstanceId"] not in instance_to_standby

    def test_standby_one_instance(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby = response["AutoScalingGroups"][0]["Instances"][0][
            "InstanceId"
        ]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 3
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 2

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        # test to ensure tag has been retained (standby instance is still part of the ASG)
        response = ec2_client.describe_instances(InstanceIds=[instance_to_standby])
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                tags = instance["Tags"]
                assert len(tags) == 2

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(response["LoadBalancerDescriptions"][0]["Instances"]) == 2
        for x in response["LoadBalancerDescriptions"][0]["Instances"]:
            assert x["InstanceId"] not in instance_to_standby

    def test_standby_elb_update(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby = response["AutoScalingGroups"][0]["Instances"][0][
            "InstanceId"
        ]

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 3
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 2

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(response["LoadBalancerDescriptions"][0]["Instances"]) == 2
        for x in response["LoadBalancerDescriptions"][0]["Instances"]:
            assert x["InstanceId"] not in instance_to_standby

    def test_standby_terminate_instance_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby_terminate = response["AutoScalingGroups"][0]["Instances"][
            0
        ]["InstanceId"]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_terminate],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 3
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 2

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        response = self.as_client.terminate_instance_in_auto_scaling_group(
            InstanceId=instance_to_standby_terminate,
            ShouldDecrementDesiredCapacity=True,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        # AWS still decrements desired capacity ASG if requested, even if the terminated instance is in standby
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 1
        assert (
            response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"]
            != instance_to_standby_terminate
        )
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 1

        response = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        assert (
            response["Reservations"][0]["Instances"][0]["State"]["Name"] == "terminated"
        )

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 1
        for x in response["LoadBalancerDescriptions"][0]["Instances"]:
            assert x["InstanceId"] not in instance_to_standby_terminate

    def test_standby_terminate_instance_no_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby_terminate = response["AutoScalingGroups"][0]["Instances"][
            0
        ]["InstanceId"]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_terminate],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 3
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 2

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        response = self.as_client.terminate_instance_in_auto_scaling_group(
            InstanceId=instance_to_standby_terminate,
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        group = response["AutoScalingGroups"][0]
        assert len(group["Instances"]) == 2
        assert instance_to_standby_terminate not in [
            x["InstanceId"] for x in group["Instances"]
        ]
        assert group["DesiredCapacity"] == 2

        response = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        assert (
            response["Reservations"][0]["Instances"][0]["State"]["Name"] == "terminated"
        )

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(response["LoadBalancerDescriptions"][0]["Instances"]) == 2
        for x in response["LoadBalancerDescriptions"][0]["Instances"]:
            assert x["InstanceId"] not in instance_to_standby_terminate

    def test_standby_detach_instance_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby_detach = response["AutoScalingGroups"][0]["Instances"][0][
            "InstanceId"
        ]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_detach],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 3
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 2

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_detach]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        response = self.as_client.detach_instances(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_detach],
            ShouldDecrementDesiredCapacity=True,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        # AWS still decrements desired capacity ASG if requested, even if the detached instance was in standby
        group = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )["AutoScalingGroups"][0]
        assert len(group["Instances"]) == 1
        assert group["Instances"][0]["InstanceId"] != instance_to_standby_detach
        assert group["DesiredCapacity"] == 1

        instance = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_detach]
        )["Reservations"][0]["Instances"][0]
        assert instance["State"]["Name"] == "running"

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(response["LoadBalancerDescriptions"][0]["Instances"]) == 1
        for x in response["LoadBalancerDescriptions"][0]["Instances"]:
            assert x["InstanceId"] not in instance_to_standby_detach

    def test_standby_detach_instance_no_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby_detach = response["AutoScalingGroups"][0]["Instances"][0][
            "InstanceId"
        ]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_detach],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 3
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 2

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_detach]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        response = self.as_client.detach_instances(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_detach],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        group = response["AutoScalingGroups"][0]
        assert len(group["Instances"]) == 2
        assert instance_to_standby_detach not in [
            x["InstanceId"] for x in group["Instances"]
        ]
        assert group["DesiredCapacity"] == 2

        instance = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_detach]
        )["Reservations"][0]["Instances"][0]
        assert instance["State"]["Name"] == "running"

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 2
        for x in response["LoadBalancerDescriptions"][0]["Instances"]:
            assert x["InstanceId"] not in instance_to_standby_detach

    def test_standby_exit_standby(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instance_to_standby_exit_standby = response["AutoScalingGroups"][0][
            "Instances"
        ][0]["InstanceId"]

        ec2_client = boto3.client("ec2", region_name="us-east-1")

        response = self.as_client.enter_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_exit_standby],
            ShouldDecrementDesiredCapacity=False,
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert len(response["AutoScalingGroups"][0]["Instances"]) == 3
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 2

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_exit_standby]
        )
        assert response["AutoScalingInstances"][0]["LifecycleState"] == "Standby"

        response = self.as_client.exit_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_exit_standby],
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        group = response["AutoScalingGroups"][0]
        assert len(group["Instances"]) == 3
        assert instance_to_standby_exit_standby in [
            x["InstanceId"] for x in group["Instances"]
        ]
        assert group["DesiredCapacity"] == 3

        instance = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_exit_standby]
        )["Reservations"][0]["Instances"][0]
        assert instance["State"]["Name"] == "running"

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 3
        assert instance_to_standby_exit_standby in [
            x["InstanceId"]
            for x in response["LoadBalancerDescriptions"][0]["Instances"]
        ]


@mock_aws
class TestAutoScalingInstancesProtected(TestCase):
    def setUp(self) -> None:
        self.mocked_networking = setup_networking()
        self.as_client = boto3.client("autoscaling", region_name="us-east-1")
        self.elb_client = boto3.client("elb", region_name="us-east-1")

        self.asg_name = str(uuid4())
        self.lb_name = str(uuid4())
        self.lc_name = str(uuid4())
        self.as_client.create_launch_configuration(
            LaunchConfigurationName=self.lc_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )

        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            MinSize=0,
            MaxSize=4,
            DesiredCapacity=2,
            Tags=[
                {
                    "ResourceId": self.asg_name,
                    "Key": "test_key",
                    "Value": "test_value",
                    "PropagateAtLaunch": True,
                }
            ],
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=True,
        )

        self.elb_client.create_load_balancer(
            LoadBalancerName=self.lb_name,
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )

        response = self.as_client.attach_load_balancers(
            AutoScalingGroupName=self.asg_name, LoadBalancerNames=[self.lb_name]
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    def test_attach_one_instance(self):
        ec2 = boto3.resource("ec2", "us-east-1")
        instances_to_add = [
            x.id
            for x in ec2.create_instances(
                ImageId=EXAMPLE_AMI_ID, MinCount=1, MaxCount=1
            )
        ]

        response = self.as_client.attach_instances(
            AutoScalingGroupName=self.asg_name, InstanceIds=instances_to_add
        )
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instances = response["AutoScalingGroups"][0]["Instances"]
        assert len(instances) == 3
        for instance in instances:
            assert instance["ProtectedFromScaleIn"] is True

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 3


@mock_aws
class TestAutoScalingTerminateInstances(TestCase):
    def setUp(self) -> None:
        self.mocked_networking = setup_networking()
        self.as_client = boto3.client("autoscaling", region_name="us-east-1")
        self.elb_client = boto3.client("elb", region_name="us-east-1")
        self.lb_name = str(uuid4())
        self.lc_name = str(uuid4())
        self.asg_name = str(uuid4())

        self.as_client.create_launch_configuration(
            LaunchConfigurationName=self.lc_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=self.asg_name,
            LaunchConfigurationName=self.lc_name,
            MinSize=0,
            DesiredCapacity=1,
            MaxSize=2,
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
            NewInstancesProtectedFromScaleIn=False,
        )
        self.elb_client.create_load_balancer(
            LoadBalancerName=self.lb_name,
            Listeners=[
                {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080}
            ],
            AvailabilityZones=["us-east-1a", "us-east-1b"],
        )
        self.as_client.attach_load_balancers(
            AutoScalingGroupName=self.asg_name, LoadBalancerNames=[self.lb_name]
        )

    def test_terminate_instance_in_auto_scaling_group_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        original_instance_id = next(
            instance["InstanceId"]
            for instance in response["AutoScalingGroups"][0]["Instances"]
        )
        self.as_client.terminate_instance_in_auto_scaling_group(
            InstanceId=original_instance_id, ShouldDecrementDesiredCapacity=True
        )

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        assert response["AutoScalingGroups"][0]["Instances"] == []
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 0

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 0

    def test_terminate_instance_in_auto_scaling_group_no_decrement(self):
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        original_instance_id = next(
            instance["InstanceId"]
            for instance in response["AutoScalingGroups"][0]["Instances"]
        )
        self.as_client.terminate_instance_in_auto_scaling_group(
            InstanceId=original_instance_id, ShouldDecrementDesiredCapacity=False
        )

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        replaced_instance_id = next(
            instance["InstanceId"]
            for instance in response["AutoScalingGroups"][0]["Instances"]
        )
        assert replaced_instance_id != original_instance_id
        assert response["AutoScalingGroups"][0]["DesiredCapacity"] == 1

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        assert len(list(response["LoadBalancerDescriptions"][0]["Instances"])) == 1
        assert original_instance_id not in [
            x["InstanceId"]
            for x in response["LoadBalancerDescriptions"][0]["Instances"]
        ]
