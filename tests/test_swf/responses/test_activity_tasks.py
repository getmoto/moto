import re
from unittest import SkipTest

from botocore.exceptions import ClientError
from freezegun import freeze_time
import pytest

from moto import mock_swf
from moto import settings

from ..utils import SCHEDULE_ACTIVITY_TASK_DECISION
from ..utils import setup_workflow_boto3


# PollForActivityTask endpoint


@mock_swf
def test_poll_for_activity_task_when_one_boto3():
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    resp = client.poll_for_activity_task(
        domain="test-domain",
        taskList={"name": "activity-task-list"},
        identity="surprise",
    )
    assert resp["activityId"] == "my-activity-001"
    assert re.match("[-a-z0-9]+", resp["taskToken"])

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    assert resp["events"][-1]["eventType"] == "ActivityTaskStarted"
    assert resp["events"][-1]["activityTaskStartedEventAttributes"] == {
        "identity": "surprise",
        "scheduledEventId": 5,
    }


@pytest.mark.parametrize("task_name", ["activity-task-list", "non-existent-queue"])
@mock_swf
def test_poll_for_activity_task_when_none_boto3(task_name):
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": task_name}
    )
    assert "taskToken" not in resp
    assert resp["startedEventId"] == 0
    assert resp["previousStartedEventId"] == 0


# CountPendingActivityTasks endpoint


@pytest.mark.parametrize(
    "task_name,cnt", [("activity-task-list", 1), ("non-existent", 0)]
)
@mock_swf
def test_count_pending_activity_tasks_boto3(task_name, cnt):
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )

    resp = client.count_pending_activity_tasks(
        domain="test-domain", taskList={"name": task_name}
    )
    assert resp["count"] == cnt
    assert resp["truncated"] is False


# RespondActivityTaskCompleted endpoint


@mock_swf
def test_respond_activity_task_completed_boto3():
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = client.poll_for_activity_task(
        domain="test-domain", taskList={"name": "activity-task-list"}
    )["taskToken"]

    client.respond_activity_task_completed(
        taskToken=activity_token, result="result of the task"
    )

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    assert resp["events"][-2]["eventType"] == "ActivityTaskCompleted"
    assert resp["events"][-2]["activityTaskCompletedEventAttributes"] == {
        "result": "result of the task",
        "scheduledEventId": 5,
        "startedEventId": 6,
    }


@mock_swf
def test_respond_activity_task_completed_on_closed_workflow_execution_boto3():
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = client.poll_for_activity_task(
        domain="test-domain", taskList={"name": "activity-task-list"}
    )["taskToken"]

    client.terminate_workflow_execution(domain="test-domain", workflowId="uid-abcd1234")

    with pytest.raises(ClientError) as ex:
        client.respond_activity_task_completed(taskToken=activity_token)
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        f"Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId={client.run_id}]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_respond_activity_task_completed_with_task_already_completed_boto3():
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = client.poll_for_activity_task(
        domain="test-domain", taskList={"name": "activity-task-list"}
    )["taskToken"]

    client.respond_activity_task_completed(taskToken=activity_token)

    with pytest.raises(ClientError) as ex:
        client.respond_activity_task_completed(taskToken=activity_token)
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown activity, scheduledEventId = 5"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# RespondActivityTaskFailed endpoint


@mock_swf
def test_respond_activity_task_failed_boto3():
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = client.poll_for_activity_task(
        domain="test-domain", taskList={"name": "activity-task-list"}
    )["taskToken"]

    client.respond_activity_task_failed(
        taskToken=activity_token, reason="short reason", details="long details"
    )

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    assert resp["events"][-2]["eventType"] == "ActivityTaskFailed"
    assert resp["events"][-2]["activityTaskFailedEventAttributes"] == {
        "reason": "short reason",
        "details": "long details",
        "scheduledEventId": 5,
        "startedEventId": 6,
    }


@mock_swf
def test_respond_activity_task_completed_with_wrong_token_boto3():
    # NB: we just test ONE failure case for RespondActivityTaskFailed
    # because the safeguards are shared with RespondActivityTaskCompleted, so
    # no need to retest everything end-to-end.
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    _ = client.poll_for_activity_task(
        domain="test-domain", taskList={"name": "activity-task-list"}
    )["taskToken"]

    with pytest.raises(ClientError) as ex:
        client.respond_activity_task_failed(taskToken="not-a-correct-token")
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == "Invalid token"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# RecordActivityTaskHeartbeat endpoint


@mock_swf
def test_record_activity_task_heartbeat_boto3():
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    activity_token = client.poll_for_activity_task(
        domain="test-domain", taskList={"name": "activity-task-list"}
    )["taskToken"]

    resp = client.record_activity_task_heartbeat(taskToken=activity_token)
    assert resp["cancelRequested"] is False


@mock_swf
def test_record_activity_task_heartbeat_with_wrong_token_boto3():
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )
    _ = client.poll_for_activity_task(
        domain="test-domain", taskList={"name": "activity-task-list"}
    )["taskToken"]

    with pytest.raises(ClientError) as ex:
        client.record_activity_task_heartbeat(taskToken="bad-token")
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == "Invalid token"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_record_activity_task_heartbeat_sets_details_in_case_of_timeout_boto3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to manipulate time in ServerMode")
    client = setup_workflow_boto3()
    decision_token = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )["taskToken"]
    client.respond_decision_task_completed(
        taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
    )

    with freeze_time("2015-01-01 12:00:00"):
        activity_token = client.poll_for_activity_task(
            domain="test-domain", taskList={"name": "activity-task-list"}
        )["taskToken"]
        client.record_activity_task_heartbeat(
            taskToken=activity_token, details="some progress details"
        )

    with freeze_time("2015-01-01 12:05:30"):
        # => Activity Task Heartbeat timeout reached!!
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )
        assert resp["events"][-2]["eventType"] == "ActivityTaskTimedOut"
        attrs = resp["events"][-2]["activityTaskTimedOutEventAttributes"]
        assert attrs["details"] == "some progress details"
