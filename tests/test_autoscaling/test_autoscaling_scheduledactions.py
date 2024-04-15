from datetime import datetime
from unittest import TestCase

import boto3
from botocore.exceptions import ClientError
from pytest import raises

from moto import mock_aws


@mock_aws
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
        assert len(actions) == 30

    def test_non_existing_group_name(self):
        self._create_scheduled_action(name="my-scheduled-action", idx=1)

        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName="wrong_group"
        )
        actions = response["ScheduledUpdateGroupActions"]
        # since there is no such group name, no actions have been returned
        assert len(actions) == 0

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
        assert len(actions) == 40

    def test_scheduled_action_delete(self):
        for i in range(3):
            self._create_scheduled_action(name=f"my-scheduled-action-{i}", idx=i)

        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = response["ScheduledUpdateGroupActions"]
        assert len(actions) == 3

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
        assert len(actions) == 1

    def test_delete_nonexistent_action(self) -> None:
        with raises(ClientError) as exc_info:
            self.client.delete_scheduled_action(
                AutoScalingGroupName=self.asg_name,
                ScheduledActionName="nonexistent",
            )
        assert exc_info.value.response["Error"]["Code"] == "ValidationError"
        assert (
            exc_info.value.response["Error"]["Message"]
            == "Scheduled action name not found"
        )

    def test_put_actions_content(self) -> None:
        # actions with different combinations of properties return the correct content
        self.client.batch_put_scheduled_update_group_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledUpdateGroupActions=[
                {
                    "ScheduledActionName": "desired-capacity-with-start-time",
                    "DesiredCapacity": 1,
                    "StartTime": "2024-01-18T09:00:00Z",
                },
                {
                    "ScheduledActionName": "min-size-with-recurrence",
                    "MinSize": 3,
                    "Recurrence": "* * * * *",
                },
                {
                    "ScheduledActionName": "complete",
                    "MinSize": 1,
                    "DesiredCapacity": 2,
                    "MaxSize": 3,
                    "Recurrence": "* * * * *",
                    "StartTime": "2024-01-19T09:00:00Z",
                    "EndTime": "2024-01-20T09:00:00Z",
                    "TimeZone": "America/New_York",
                },
            ],
        )
        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = response["ScheduledUpdateGroupActions"]
        assert len(actions) == 3

        desired_capacity_action = next(
            filter(
                lambda action: action["ScheduledActionName"]
                == "desired-capacity-with-start-time",
                actions,
            )
        )
        assert desired_capacity_action["DesiredCapacity"] == 1
        assert desired_capacity_action["StartTime"] == datetime.fromisoformat(
            "2024-01-18T09:00:00+00:00"
        )
        assert "MinSize" not in desired_capacity_action
        assert "MaxSize" not in desired_capacity_action
        assert "TimeZone" not in desired_capacity_action
        assert "Recurrence" not in desired_capacity_action
        assert "EndTime" not in desired_capacity_action

        min_size_action = next(
            filter(
                lambda action: action["ScheduledActionName"]
                == "min-size-with-recurrence",
                actions,
            )
        )
        assert min_size_action["MinSize"] == 3
        assert min_size_action["Recurrence"] == "* * * * *"
        assert "DesiredCapacity" not in min_size_action
        assert "MaxSize" not in min_size_action
        assert "TimeZone" not in min_size_action
        # StartTime may be present
        assert "EndTime" not in min_size_action

        complete_action = next(
            filter(lambda action: action["ScheduledActionName"] == "complete", actions)
        )
        assert complete_action["MinSize"] == 1
        assert complete_action["DesiredCapacity"] == 2
        assert complete_action["MaxSize"] == 3
        assert complete_action["Recurrence"] == "* * * * *"
        assert complete_action["StartTime"] == datetime.fromisoformat(
            "2024-01-19T09:00:00+00:00"
        )
        assert complete_action["EndTime"] == datetime.fromisoformat(
            "2024-01-20T09:00:00+00:00"
        )
        assert complete_action["TimeZone"] == "America/New_York"

    def test_put_replaces_action_with_same_name(self) -> None:
        self.client.put_scheduled_update_group_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionName="my-action",
            Recurrence="* * * * *",
            MinSize=3,
        )
        self.client.put_scheduled_update_group_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionName="my-action",
            Recurrence="* * * * *",
            DesiredCapacity=2,
        )

        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = response["ScheduledUpdateGroupActions"]
        assert len(actions) == 1

        assert actions[0]["DesiredCapacity"] == 2
        assert "MinSize" not in actions[0]

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
            TimeZone="Etc/UTC",
        )

    def test_batch_put_scheduled_group_action(self) -> None:
        put_response = self.client.batch_put_scheduled_update_group_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledUpdateGroupActions=[
                {
                    "ScheduledActionName": "StartAction",
                    "Recurrence": "0 9 * * 1-5",
                    "MinSize": 1,
                    "MaxSize": 1,
                    "DesiredCapacity": 1,
                },
                {
                    "ScheduledActionName": "StopAction",
                    "Recurrence": "0 17 * * 1-5",
                    "MinSize": 0,
                    "MaxSize": 0,
                    "DesiredCapacity": 0,
                },
            ],
        )
        assert len(put_response["FailedScheduledUpdateGroupActions"]) == 0

        response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = response["ScheduledUpdateGroupActions"]
        assert len(actions) == 2

    def test_batch_delete_scheduled_action(self) -> None:
        action_names = [f"my-action-{i}" for i in range(10)]
        for j, action_name in enumerate(action_names):
            self._create_scheduled_action(action_name, j)
        delete_response = self.client.batch_delete_scheduled_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionNames=action_names[::2],  # delete even indices
        )
        assert len(delete_response["FailedScheduledActions"]) == 0

        describe_response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = describe_response["ScheduledUpdateGroupActions"]
        assert len(actions) == 5

        delete_response = self.client.batch_delete_scheduled_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionNames=action_names[1::2],  # delete odd indices
        )
        assert len(delete_response["FailedScheduledActions"]) == 0

        describe_response = self.client.describe_scheduled_actions(
            AutoScalingGroupName=self.asg_name
        )
        actions = describe_response["ScheduledUpdateGroupActions"]
        assert len(actions) == 0

    def test_batch_delete_nonexistent_action(self) -> None:
        action_name = "nonexistent"
        response = self.client.batch_delete_scheduled_action(
            AutoScalingGroupName=self.asg_name,
            ScheduledActionNames=[action_name],
        )
        assert len(response["FailedScheduledActions"]) == 1
        assert response["FailedScheduledActions"][0] == {
            "ScheduledActionName": action_name,
            "ErrorCode": "ValidationError",
            "ErrorMessage": "Scheduled action name not found",
        }
