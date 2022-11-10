import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_autoscaling
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID
from unittest import TestCase
from .utils import setup_networking


@mock_autoscaling
class TestAutoScalingGroup(TestCase):
    def setUp(self) -> None:
        self.mocked_networking = setup_networking()
        self.as_client = boto3.client("autoscaling", region_name="us-east-1")
        self.lc_name = "tester_config"
        self.as_client.create_launch_configuration(
            LaunchConfigurationName=self.lc_name,
            ImageId=EXAMPLE_AMI_ID,
            InstanceType="t2.medium",
        )

    def test_create_autoscaling_groups_defaults(self):
        """Test with the minimum inputs and check that all of the proper defaults
        are assigned for the other attributes"""

        self._create_group(name="tester_group")

        group = self.as_client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
        group["AutoScalingGroupName"].should.equal("tester_group")
        group["MaxSize"].should.equal(2)
        group["MinSize"].should.equal(1)
        group["LaunchConfigurationName"].should.equal(self.lc_name)

        # Defaults
        group["AvailabilityZones"].should.equal(["us-east-1a"])  # subnet1
        group["DesiredCapacity"].should.equal(1)
        group["VPCZoneIdentifier"].should.equal(self.mocked_networking["subnet1"])
        group["DefaultCooldown"].should.equal(300)
        group["HealthCheckGracePeriod"].should.equal(300)
        group["HealthCheckType"].should.equal("EC2")
        group["LoadBalancerNames"].should.equal([])
        group.shouldnt.have.key("PlacementGroup")
        group["TerminationPolicies"].should.equal(["Default"])
        group["Tags"].should.equal([])

    def test_create_autoscaling_group__additional_params(self):
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName="tester_group",
            MinSize=1,
            MaxSize=2,
            LaunchConfigurationName=self.lc_name,
            CapacityRebalance=True,
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )

        group = self.as_client.describe_auto_scaling_groups()["AutoScalingGroups"][0]
        group["AutoScalingGroupName"].should.equal("tester_group")
        group["CapacityRebalance"].should.equal(True)

    def test_list_many_autoscaling_groups(self):

        for i in range(51):
            self._create_group("TestGroup%d" % i)

        response = self.as_client.describe_auto_scaling_groups()
        groups = response["AutoScalingGroups"]
        marker = response["NextToken"]
        groups.should.have.length_of(50)
        marker.should.equal(groups[-1]["AutoScalingGroupName"])

        response2 = self.as_client.describe_auto_scaling_groups(NextToken=marker)

        groups.extend(response2["AutoScalingGroups"])
        groups.should.have.length_of(51)
        assert "NextToken" not in response2.keys()

    def test_autoscaling_group_delete(self):
        self._create_group(name="tester_group")

        groups = self.as_client.describe_auto_scaling_groups()["AutoScalingGroups"]
        groups.should.have.length_of(1)

        self.as_client.delete_auto_scaling_group(AutoScalingGroupName="tester_group")

        groups = self.as_client.describe_auto_scaling_groups()["AutoScalingGroups"]
        groups.should.have.length_of(0)

    def test_describe_autoscaling_groups__instances(self):
        self._create_group(name="test_asg")

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test_asg"]
        )
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
        group = response["AutoScalingGroups"][0]
        group["AutoScalingGroupARN"].should.match(
            f"arn:aws:autoscaling:us-east-1:{ACCOUNT_ID}:autoScalingGroup:"
        )
        group["AutoScalingGroupName"].should.equal("test_asg")
        group["LaunchConfigurationName"].should.equal(self.lc_name)
        group.should_not.have.key("LaunchTemplate")
        group["AvailabilityZones"].should.equal(["us-east-1a"])
        group["VPCZoneIdentifier"].should.equal(self.mocked_networking["subnet1"])
        for instance in group["Instances"]:
            instance["LaunchConfigurationName"].should.equal(self.lc_name)
            instance.should_not.have.key("LaunchTemplate")
            instance["AvailabilityZone"].should.equal("us-east-1a")
            instance["InstanceType"].should.equal("t2.medium")

    def test_set_instance_health(self):
        self._create_group(name="test_asg")

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test_asg"]
        )

        instance1 = response["AutoScalingGroups"][0]["Instances"][0]
        instance1["HealthStatus"].should.equal("Healthy")

        self.as_client.set_instance_health(
            InstanceId=instance1["InstanceId"], HealthStatus="Unhealthy"
        )

        response = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test_asg"]
        )

        instance1 = response["AutoScalingGroups"][0]["Instances"][0]
        instance1["HealthStatus"].should.equal("Unhealthy")

    def test_suspend_processes(self):
        self._create_group(name="test-asg")

        # When we suspend the 'Launch' process on the ASG client
        self.as_client.suspend_processes(
            AutoScalingGroupName="test-asg", ScalingProcesses=["Launch"]
        )

        res = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test-asg"]
        )

        # The 'Launch' process should, in fact, be suspended
        launch_suspended = False
        for proc in res["AutoScalingGroups"][0]["SuspendedProcesses"]:
            if proc.get("ProcessName") == "Launch":
                launch_suspended = True

        assert launch_suspended is True

    def test_suspend_processes_all_by_default(self):
        self._create_group(name="test-asg")

        # When we suspend with no processes specified
        self.as_client.suspend_processes(AutoScalingGroupName="test-asg")

        res = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test-asg"]
        )

        # All processes should be suspended
        all_proc_names = [
            "Launch",
            "Terminate",
            "AddToLoadBalancer",
            "AlarmNotification",
            "AZRebalance",
            "HealthCheck",
            "InstanceRefresh",
            "ReplaceUnhealthy",
            "ScheduledActions",
        ]
        suspended_proc_names = [
            proc["ProcessName"]
            for proc in res["AutoScalingGroups"][0]["SuspendedProcesses"]
        ]
        set(suspended_proc_names).should.equal(set(all_proc_names))

    def test_suspend_additional_processes(self):
        self._create_group(name="test-asg")

        # When we suspend the 'Launch' and 'Terminate' processes in separate calls
        self.as_client.suspend_processes(
            AutoScalingGroupName="test-asg", ScalingProcesses=["Launch"]
        )
        self.as_client.suspend_processes(
            AutoScalingGroupName="test-asg", ScalingProcesses=["Terminate"]
        )

        res = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test-asg"]
        )

        # Both 'Launch' and 'Terminate' should be suspended
        launch_suspended = False
        terminate_suspended = False
        for proc in res["AutoScalingGroups"][0]["SuspendedProcesses"]:
            if proc.get("ProcessName") == "Launch":
                launch_suspended = True
            if proc.get("ProcessName") == "Terminate":
                terminate_suspended = True

        assert launch_suspended is True
        assert terminate_suspended is True

    def test_resume_processes(self):
        self._create_group(name="test-asg")

        # When we suspect 'Launch' and 'Termiate' process then resume 'Launch'
        self.as_client.suspend_processes(
            AutoScalingGroupName="test-asg", ScalingProcesses=["Launch", "Terminate"]
        )

        self.as_client.resume_processes(
            AutoScalingGroupName="test-asg", ScalingProcesses=["Launch"]
        )

        res = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test-asg"]
        )

        # Only 'Terminate' should be suspended
        expected_suspended_processes = [
            {"ProcessName": "Terminate", "SuspensionReason": ""}
        ]
        res["AutoScalingGroups"][0]["SuspendedProcesses"].should.equal(
            expected_suspended_processes
        )

    def test_resume_processes_all_by_default(self):
        self._create_group(name="test-asg")

        # When we suspend two processes then resume with no process argument
        self.as_client.suspend_processes(
            AutoScalingGroupName="test-asg", ScalingProcesses=["Launch", "Terminate"]
        )

        self.as_client.resume_processes(AutoScalingGroupName="test-asg")

        res = self.as_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=["test-asg"]
        )

        # No processes should be suspended
        res["AutoScalingGroups"][0]["SuspendedProcesses"].should.equal([])

    def _create_group(self, name):
        self.as_client.create_auto_scaling_group(
            AutoScalingGroupName=name,
            MinSize=1,
            MaxSize=2,
            LaunchConfigurationName=self.lc_name,
            VPCZoneIdentifier=self.mocked_networking["subnet1"],
        )
