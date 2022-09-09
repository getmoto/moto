import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_autoscaling
from unittest import TestCase


@mock_autoscaling
class TestAutoScalingScheduledActions(TestCase):
    def setUp(self) -> None:
        self.client = boto3.client("autoscaling", region_name="us-east-1")
        self.asg_name = "tester_group"

    def test_list_many_scheduled_scaling_actions(self):
        for i in range(30):
            self._create_scheduled_action(name=f"my-scheduled-action-{i}", idx=i)

        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = response["ScheduledUpdateGroupActions"]
        actions.should.have.length_of(30)

    def test_non_existing_group_name(self):
        self._create_scheduled_action(name="my-scheduled-action", idx=1)

        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName="wrong_group"
        )
        actions = response["ScheduledUpdateGroupActions"]
        # since there is no such group name, no actions have been returned
        actions.should.have.length_of(0)

    def test_describe_scheduled_actions_returns_all_actions_when_no_argument_is_passed(
        self,
    ):
        for i in range(30):
            self._create_scheduled_action(name=f"my-scheduled-action-{i}", idx=i)

        for i in range(10):
            self._create_scheduled_action(
                name=f"my-scheduled-action-4{i}", idx=i, asg_name="test_group-2"
            )

        response = self.client.describe_scheduled_actions()
        actions = response["ScheduledUpdateGroupActions"]

        # Since no argument is passed describe_scheduled_actions, all scheduled actions are returned
        actions.should.have.length_of(40)

    def test_scheduled_action_delete(self):
        for i in range(3):
            self._create_scheduled_action(name=f"my-scheduled-action-{i}", idx=i)

        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = response["ScheduledUpdateGroupActions"]
        actions.should.have.length_of(3)

        self.client.delete_scheduled_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionName="my-scheduled-action-2",
        )
        self.client.delete_scheduled_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionName="my-scheduled-action-1",
        )
        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = response["ScheduledUpdateGroupActions"]
        actions.should.have.length_of(1)

    def _create_scheduled_action(self, name, idx, asg_name=None):
        self.client.put_scheduled_update_group_action(
            AutoScalingGroupName=asg_name or self.asg_name,
            ScheduledActionName=name,
            StartTime=f"2022-07-01T00:00:{idx}Z",
            EndTime=f"2022-09-01T00:00:{idx}Z",
            Recurrence="* * * * *",
            MinSize=idx + 1,
            MaxSize=idx + 5,
            DesiredCapacity=idx + 3,
        )
