import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_autoscaling, mock_elb, mock_ec2
from .utils import setup_networking
from tests import EXAMPLE_AMI_ID
from unittest import TestCase
from uuid import uuid4


@mock_autoscaling
@mock_ec2
@mock_elb
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
        list(response["LoadBalancers"]).should.have.length_of(1)
        response["LoadBalancers"][0]["LoadBalancerName"].should.equal(self.lb_name)

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
        list(response["LoadBalancers"]).should.have.length_of(0)
        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(0)

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(self.instance_count)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        list(
            response["AutoScalingGroups"][0]["LoadBalancerNames"]
        ).should.have.length_of(1)

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(0)

        response = self.as_client.describe_load_balancers(
            AutoScalingGroupName=self.asg_name
        )
        list(response["LoadBalancers"]).should.have.length_of(0)

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
        group["AutoScalingGroupName"].should.equal(self.asg_name)
        set(group["AvailabilityZones"]).should.equal(set(["us-east-1a", "us-east-1b"]))
        group["DesiredCapacity"].should.equal(2)
        group["MaxSize"].should.equal(INSTANCE_COUNT_GROUP)
        group["MinSize"].should.equal(INSTANCE_COUNT_GROUP)
        group["Instances"].should.have.length_of(INSTANCE_COUNT_GROUP)
        group["VPCZoneIdentifier"].should.equal(
            f"{self.mocked_networking['subnet1']},{self.mocked_networking['subnet2']}"
        )
        group["LaunchConfigurationName"].should.equal(self.lc_name)
        group["DefaultCooldown"].should.equal(60)
        group["HealthCheckGracePeriod"].should.equal(100)
        group["HealthCheckType"].should.equal("EC2")
        group["LoadBalancerNames"].should.equal([self.lb_name])
        group["PlacementGroup"].should.equal("test_placement")
        list(group["TerminationPolicies"]).should.equal(
            ["OldestInstance", "NewestInstance"]
        )
        list(group["Tags"]).should.have.length_of(1)
        tag = group["Tags"][0]
        tag["ResourceId"].should.equal(self.asg_name)
        tag["Key"].should.equal("test_key")
        tag["Value"].should.equal("test_value")
        tag["PropagateAtLaunch"].should.equal(True)

        instances_attached = self.elb_client.describe_instance_health(
            LoadBalancerName=self.lb_name
        )["InstanceStates"]
        instances_attached.should.have.length_of(
            INSTANCE_COUNT_START + INSTANCE_COUNT_GROUP
        )
        attached_ids = [i["InstanceId"] for i in instances_attached]
        for ec2_instance_id in instances_ids:
            attached_ids.should.contain(ec2_instance_id)

        scheduled_actions = self.as_client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        scheduled_action_1 = scheduled_actions["ScheduledUpdateGroupActions"][0]
        scheduled_action_1["AutoScalingGroupName"].should.equal(self.asg_name)
        scheduled_action_1["DesiredCapacity"].should.equal(9)
        scheduled_action_1["MaxSize"].should.equal(12)
        scheduled_action_1["MinSize"].should.equal(5)
        scheduled_action_1.should.contain("StartTime")
        scheduled_action_1.should.contain("EndTime")
        scheduled_action_1["Recurrence"].should.equal("* * * * *")
        scheduled_action_1["ScheduledActionName"].should.equal("my-scheduled-action")


@mock_autoscaling
@mock_elb
@mock_ec2
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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(1)
        instance_to_detach.shouldnt.be.within(
            [x["InstanceId"] for x in response["AutoScalingGroups"][0]["Instances"]]
        )

        # test to ensure tag has been removed
        response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        tags.should.have.length_of(1)

        # test to ensure tag is present on other instance
        response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        tags.should.have.length_of(2)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(1)
        instance_to_detach.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        # test to ensure instance was replaced
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(2)

        response = ec2_client.describe_instances(InstanceIds=[instance_to_detach])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        tags.should.have.length_of(1)

        response = ec2_client.describe_instances(InstanceIds=[instance_to_keep])
        tags = response["Reservations"][0]["Instances"][0]["Tags"]
        tags.should.have.length_of(2)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(2)
        instance_to_detach.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(2)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        # test to ensure tag has been retained (standby instance is still part of the ASG)
        response = ec2_client.describe_instances(InstanceIds=[instance_to_standby])
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                tags = instance["Tags"]
                tags.should.have.length_of(2)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(1)
        instance_to_standby.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        # test to ensure tag has been retained (standby instance is still part of the ASG)
        response = ec2_client.describe_instances(InstanceIds=[instance_to_standby])
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                tags = instance["Tags"]
                tags.should.have.length_of(2)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(2)
        instance_to_standby.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(2)
        instance_to_standby.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        response = self.as_client.terminate_instance_in_auto_scaling_group(
            InstanceId=instance_to_standby_terminate,
            ShouldDecrementDesiredCapacity=True,
        )
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        # AWS still decrements desired capacity ASG if requested, even if the terminated instance is in standby
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(1)
        response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"].should_not.equal(
            instance_to_standby_terminate
        )
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

        response = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal(
            "terminated"
        )

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(1)
        instance_to_standby_terminate.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        response = self.as_client.terminate_instance_in_auto_scaling_group(
            InstanceId=instance_to_standby_terminate,
            ShouldDecrementDesiredCapacity=False,
        )
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        group = response["AutoScalingGroups"][0]
        group["Instances"].should.have.length_of(2)
        instance_to_standby_terminate.shouldnt.be.within(
            [x["InstanceId"] for x in group["Instances"]]
        )
        group["DesiredCapacity"].should.equal(2)

        response = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_terminate]
        )
        response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal(
            "terminated"
        )

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(2)
        instance_to_standby_terminate.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_detach]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        response = self.as_client.detach_instances(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_detach],
            ShouldDecrementDesiredCapacity=True,
        )
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        # AWS still decrements desired capacity ASG if requested, even if the detached instance was in standby
        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(1)
        response["AutoScalingGroups"][0]["Instances"][0]["InstanceId"].should_not.equal(
            instance_to_standby_detach
        )
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

        response = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_detach]
        )
        response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal(
            "running"
        )

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(1)
        instance_to_standby_detach.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_detach]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        response = self.as_client.detach_instances(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_detach],
            ShouldDecrementDesiredCapacity=False,
        )
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        group = response["AutoScalingGroups"][0]
        group["Instances"].should.have.length_of(2)
        instance_to_standby_detach.shouldnt.be.within(
            [x["InstanceId"] for x in group["Instances"]]
        )
        group["DesiredCapacity"].should.equal(2)

        response = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_detach]
        )
        response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal(
            "running"
        )

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(2)
        instance_to_standby_detach.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        response["AutoScalingGroups"][0]["Instances"].should.have.length_of(3)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(2)

        response = self.as_client.describe_auto_scaling_instances(
            InstanceIds=[instance_to_standby_exit_standby]
        )
        response["AutoScalingInstances"][0]["LifecycleState"].should.equal("Standby")

        response = self.as_client.exit_standby(
            AutoScalingGroupName=self.asg_name,
            InstanceIds=[instance_to_standby_exit_standby],
        )
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        group = response["AutoScalingGroups"][0]
        group["Instances"].should.have.length_of(3)
        instance_to_standby_exit_standby.should.be.within(
            [x["InstanceId"] for x in group["Instances"]]
        )
        group["DesiredCapacity"].should.equal(3)

        response = ec2_client.describe_instances(
            InstanceIds=[instance_to_standby_exit_standby]
        )
        response["Reservations"][0]["Instances"][0]["State"]["Name"].should.equal(
            "running"
        )

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(3)
        instance_to_standby_exit_standby.should.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )


@mock_autoscaling
@mock_elb
@mock_ec2
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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

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
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.asg_name]
        )
        instances = response["AutoScalingGroups"][0]["Instances"]
        instances.should.have.length_of(3)
        for instance in instances:
            instance["ProtectedFromScaleIn"].should.equal(True)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(3)


@mock_autoscaling
@mock_ec2
@mock_elb
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
        response["AutoScalingGroups"][0]["Instances"].should.equal([])
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(0)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(0)

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
        replaced_instance_id.should_not.equal(original_instance_id)
        response["AutoScalingGroups"][0]["DesiredCapacity"].should.equal(1)

        response = self.elb_client.describe_load_balancers(
            LoadBalancerNames=[self.lb_name]
        )
        list(
            response["LoadBalancerDescriptions"][0]["Instances"]
        ).should.have.length_of(1)
        original_instance_id.shouldnt.be.within(
            [
                x["InstanceId"]
                for x in response["LoadBalancerDescriptions"][0]["Instances"]
            ]
        )
