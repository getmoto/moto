from datetime import datetime
import re
from time import sleep

from botocore.exceptions import ClientError
from dateutil.parser import parse as dtparse
from freezegun import freeze_time
import pytest

from moto import mock_swf, settings

from ..utils import setup_workflow_boto3


# PollForDecisionTask endpoint


@mock_swf
def test_poll_for_decision_task_when_one_boto3():
    client = setup_workflow_boto3()

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == ["WorkflowExecutionStarted", "DecisionTaskScheduled"]

    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}, identity="srv01"
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
    ]

    assert (
        resp["events"][-1]["decisionTaskStartedEventAttributes"]["identity"] == "srv01"
    )


@mock_swf
def test_poll_for_decision_task_previous_started_event_id_boto3():
    client = setup_workflow_boto3()

    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert resp["workflowExecution"]["runId"] == client.run_id
    assert "previousStartedEventId" not in resp

    # Require a failing decision, in this case a non-existant activity type
    attrs = {
        "activityId": "spam",
        "activityType": {"name": "test-activity", "version": "v1.42"},
        "taskList": {"name": "eggs"},
    }
    decision = {
        "decisionType": "ScheduleActivityTask",
        "scheduleActivityTaskDecisionAttributes": attrs,
    }
    client.respond_decision_task_completed(
        taskToken=resp["taskToken"], decisions=[decision]
    )
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert resp["workflowExecution"]["runId"] == client.run_id
    assert resp["previousStartedEventId"] == 3


@mock_swf
def test_poll_for_decision_task_ensure_single_started_task():
    client = setup_workflow_boto3()

    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert "taskToken" in resp
    first_decision_task = resp["taskToken"]

    # History should have just the decision task triggered on workflow start
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
    ]

    # Schedule another decision task, before first one is completed
    client.signal_workflow_execution(
        domain="test-domain",
        signalName="my_signal",
        workflowId="uid-abcd1234",
        input="my_input",
        runId=client.run_id,
    )

    # Second poll should return no new tasks
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert resp["previousStartedEventId"] == 0
    assert resp["startedEventId"] == 0
    assert "taskToken" not in resp

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "WorkflowExecutionSignaled",
        "DecisionTaskScheduled",
    ]

    client.respond_decision_task_completed(taskToken=first_decision_task)

    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert "taskToken" in resp

    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "WorkflowExecutionSignaled",
        "DecisionTaskScheduled",
        "DecisionTaskCompleted",
        "DecisionTaskStarted",
    ]


@mock_swf
def test_poll_for_decision_task_exclude_completed_executions():
    client = setup_workflow_boto3()

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == ["WorkflowExecutionStarted", "DecisionTaskScheduled"]

    client.terminate_workflow_execution(
        domain="test-domain", runId=client.run_id, workflowId="uid-abcd1234"
    )
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert "taskToken" not in resp


@mock_swf
def test_poll_for_decision_task_when_none_boto3():
    client = setup_workflow_boto3()

    client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})

    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    # this is the DecisionTask representation you get from the real SWF
    # after waiting 60s when there's no decision to be taken
    assert resp["previousStartedEventId"] == 0
    assert resp["startedEventId"] == 0


@mock_swf
def test_poll_for_decision_task_on_non_existent_queue_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "non-existent-queue"}
    )
    assert resp["previousStartedEventId"] == 0
    assert resp["startedEventId"] == 0


@mock_swf
def test_poll_for_decision_task_with_reverse_order_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}, reverseOrder=True
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "DecisionTaskStarted",
        "DecisionTaskScheduled",
        "WorkflowExecutionStarted",
    ]


# CountPendingDecisionTasks endpoint


@mock_swf
def test_count_pending_decision_tasks_boto3():
    client = setup_workflow_boto3()
    client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})
    resp = client.count_pending_decision_tasks(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert resp["count"] == 1
    assert resp["truncated"] is False


@mock_swf
def test_count_pending_decision_tasks_on_non_existent_task_list_boto3():
    client = setup_workflow_boto3()
    resp = client.count_pending_decision_tasks(
        domain="test-domain", taskList={"name": "non-existent"}
    )
    assert resp["count"] == 0
    assert resp["truncated"] is False


@mock_swf
def test_count_pending_decision_tasks_after_decision_completes_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    client.respond_decision_task_completed(taskToken=resp["taskToken"])

    resp = client.count_pending_decision_tasks(
        domain="test-domain", taskList={"name": "queue"}
    )
    assert resp["count"] == 0
    assert resp["truncated"] is False


# RespondDecisionTaskCompleted endpoint


@mock_swf
def test_respond_decision_task_completed_with_no_decision_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    client.respond_decision_task_completed(
        taskToken=task_token, executionContext="free-form context"
    )

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
    ]
    evt = resp["events"][-1]
    assert evt["decisionTaskCompletedEventAttributes"] == {
        "executionContext": "free-form context",
        "scheduledEventId": 2,
        "startedEventId": 3,
    }

    resp = client.describe_workflow_execution(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    assert resp["latestExecutionContext"] == "free-form context"


@mock_swf
def test_respond_decision_task_completed_with_wrong_token_boto3():
    client = setup_workflow_boto3()
    client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})
    with pytest.raises(ClientError) as ex:
        client.respond_decision_task_completed(taskToken="not-a-correct-token")
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == "Invalid token"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_respond_decision_task_completed_on_close_workflow_execution_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    client.terminate_workflow_execution(domain="test-domain", workflowId="uid-abcd1234")

    with pytest.raises(ClientError) as ex:
        client.respond_decision_task_completed(taskToken=task_token)
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        f"Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId={client.run_id}]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_respond_decision_task_completed_with_task_already_completed_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]
    client.respond_decision_task_completed(taskToken=task_token)

    with pytest.raises(ClientError) as ex:
        client.respond_decision_task_completed(taskToken=task_token)
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown decision task, scheduledEventId = 2"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_respond_decision_task_completed_with_complete_workflow_execution_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "CompleteWorkflowExecution",
            "completeWorkflowExecutionDecisionAttributes": {"result": "foo bar"},
        }
    ]
    client.respond_decision_task_completed(taskToken=task_token, decisions=decisions)

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
        "WorkflowExecutionCompleted",
    ]
    assert (
        resp["events"][-1]["workflowExecutionCompletedEventAttributes"]["result"]
        == "foo bar"
    )


@mock_swf
def test_respond_decision_task_completed_with_close_decision_not_last_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {"decisionType": "CompleteWorkflowExecution"},
        {"decisionType": "WeDontCare"},
    ]

    with pytest.raises(ClientError) as ex:
        client.respond_decision_task_completed(
            taskToken=task_token, decisions=decisions
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == (
        "Close must be last decision in list"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_respond_decision_task_completed_with_invalid_decision_type_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {"decisionType": "BadDecisionType"},
        {"decisionType": "CompleteWorkflowExecution"},
    ]

    with pytest.raises(ClientError) as ex:
        client.respond_decision_task_completed(
            taskToken=task_token, decisions=decisions
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert re.search(
        "Value 'BadDecisionType' at 'decisions.1.member.decisionType'",
        ex.value.response["Error"]["Message"],
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_respond_decision_task_completed_with_missing_attributes_totally_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [{"decisionType": "StartTimer"}]

    with pytest.raises(ClientError) as ex:
        client.respond_decision_task_completed(
            taskToken=task_token, decisions=decisions
        )
    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert re.search(
        (
            "Value null at "
            "'decisions.1.member.startTimerDecisionAttributes.timerId' "
            "failed to satisfy constraint"
        ),
        ex.value.response["Error"]["Message"],
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_swf
def test_respond_decision_task_completed_with_fail_workflow_execution_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "FailWorkflowExecution",
            "failWorkflowExecutionDecisionAttributes": {
                "reason": "my rules",
                "details": "foo",
            },
        }
    ]
    client.respond_decision_task_completed(taskToken=task_token, decisions=decisions)

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
        "WorkflowExecutionFailed",
    ]
    attrs = resp["events"][-1]["workflowExecutionFailedEventAttributes"]
    assert attrs["reason"] == "my rules"
    assert attrs["details"] == "foo"


@mock_swf
@freeze_time("2015-01-01 12:00:00 UTC")
def test_respond_decision_task_completed_with_schedule_activity_task_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "ScheduleActivityTask",
            "scheduleActivityTaskDecisionAttributes": {
                "activityId": "my-activity-001",
                "activityType": {"name": "test-activity", "version": "v1.1"},
                "heartbeatTimeout": "60",
                "input": "123",
                "taskList": {"name": "my-task-list"},
            },
        }
    ]
    client.respond_decision_task_completed(taskToken=task_token, decisions=decisions)

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
        "ActivityTaskScheduled",
    ]
    assert resp["events"][-1]["activityTaskScheduledEventAttributes"] == {
        "decisionTaskCompletedEventId": 4,
        "activityId": "my-activity-001",
        "activityType": {"name": "test-activity", "version": "v1.1"},
        "heartbeatTimeout": "60",
        "input": "123",
        "taskList": {"name": "my-task-list"},
    }

    resp = client.describe_workflow_execution(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    assert isinstance(resp["latestActivityTaskTimestamp"], datetime)
    if not settings.TEST_SERVER_MODE:
        ts = resp["latestActivityTaskTimestamp"]
        assert ts == dtparse("2015-01-01 12:00:00 UTC")


@mock_swf
def test_record_marker_decision():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "RecordMarker",
            "recordMarkerDecisionAttributes": {"markerName": "TheMarker"},
        }
    ]
    client.respond_decision_task_completed(taskToken=task_token, decisions=decisions)

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
        "MarkerRecorded",
    ]
    assert resp["events"][-1]["markerRecordedEventAttributes"] == {
        "decisionTaskCompletedEventId": 4,
        "markerName": "TheMarker",
    }


@mock_swf
def test_start_and_fire_timer_decision():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "StartTimer",
            "startTimerDecisionAttributes": {
                "startToFireTimeout": "1",
                "timerId": "timer1",
            },
        }
    ]
    client.respond_decision_task_completed(taskToken=task_token, decisions=decisions)
    sleep(1.1)

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
        "TimerStarted",
        "TimerFired",
        "DecisionTaskScheduled",
    ]
    assert resp["events"][-3]["timerStartedEventAttributes"] == {
        "decisionTaskCompletedEventId": 4,
        "startToFireTimeout": "1",
        "timerId": "timer1",
    }
    assert resp["events"][-2]["timerFiredEventAttributes"] == {
        "startedEventId": 5,
        "timerId": "timer1",
    }


@mock_swf
def test_cancel_workflow_decision():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "CancelWorkflowExecution",
            "cancelWorkflowExecutionDecisionAttributes": {
                "details": "decide to cancel"
            },
        }
    ]
    client.respond_decision_task_completed(taskToken=task_token, decisions=decisions)

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    assert types == [
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
        "WorkflowExecutionCanceled",
    ]
    assert resp["events"][-1]["workflowExecutionCanceledEventAttributes"] == {
        "decisionTaskCompletedEventId": 4,
        "details": "decide to cancel",
    }
    workflow_result = client.describe_workflow_execution(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )["executionInfo"]
    assert "closeTimestamp" in workflow_result
    assert workflow_result["executionStatus"] == "CLOSED"
    assert workflow_result["closeStatus"] == "CANCELED"
    assert workflow_result["cancelRequested"] is True
