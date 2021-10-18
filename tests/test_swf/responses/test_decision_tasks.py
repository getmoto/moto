from boto.swf.exceptions import SWFResponseError
from botocore.exceptions import ClientError
from datetime import datetime
from freezegun import freeze_time
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_swf_deprecated, mock_swf, settings
from moto.swf import swf_backend

from ..utils import setup_workflow, setup_workflow_boto3


# PollForDecisionTask endpoint
# Has boto3 equivalent
@mock_swf_deprecated
def test_poll_for_decision_task_when_one():
    conn = setup_workflow()

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])

    resp = conn.poll_for_decision_task("test-domain", "queue", identity="srv01")
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        ["WorkflowExecutionStarted", "DecisionTaskScheduled", "DecisionTaskStarted"]
    )

    resp["events"][-1]["decisionTaskStartedEventAttributes"]["identity"].should.equal(
        "srv01"
    )


@mock_swf
def test_poll_for_decision_task_when_one_boto3():
    client = setup_workflow_boto3()

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])

    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}, identity="srv01"
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        ["WorkflowExecutionStarted", "DecisionTaskScheduled", "DecisionTaskStarted"]
    )

    resp["events"][-1]["decisionTaskStartedEventAttributes"]["identity"].should.equal(
        "srv01"
    )


# Has boto3 equivalent
@mock_swf_deprecated
def test_poll_for_decision_task_previous_started_event_id():
    conn = setup_workflow()

    resp = conn.poll_for_decision_task("test-domain", "queue")
    assert resp["workflowExecution"]["runId"] == conn.run_id
    assert "previousStartedEventId" not in resp

    # Require a failing decision, in this case a non-existant activity type
    attrs = {
        "activityId": "spam",
        "activityType": {"name": "test-activity", "version": "v1.42"},
        "taskList": "eggs",
    }
    decision = {
        "decisionType": "ScheduleActivityTask",
        "scheduleActivityTaskDecisionAttributes": attrs,
    }
    conn.respond_decision_task_completed(resp["taskToken"], decisions=[decision])
    resp = conn.poll_for_decision_task("test-domain", "queue")
    assert resp["workflowExecution"]["runId"] == conn.run_id
    assert resp["previousStartedEventId"] == 3


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


# Has boto3 equivalent
@mock_swf_deprecated
def test_poll_for_decision_task_when_none():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")

    resp = conn.poll_for_decision_task("test-domain", "queue")
    # this is the DecisionTask representation you get from the real SWF
    # after waiting 60s when there's no decision to be taken
    resp.should.equal({"previousStartedEventId": 0, "startedEventId": 0})


@mock_swf
def test_poll_for_decision_task_when_none_boto3():
    client = setup_workflow_boto3()

    client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})

    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}
    )
    # this is the DecisionTask representation you get from the real SWF
    # after waiting 60s when there's no decision to be taken
    resp.should.have.key("previousStartedEventId").equal(0)
    resp.should.have.key("startedEventId").equal(0)


# Has boto3 equivalent
@mock_swf_deprecated
def test_poll_for_decision_task_on_non_existent_queue():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "non-existent-queue")
    resp.should.equal({"previousStartedEventId": 0, "startedEventId": 0})


@mock_swf
def test_poll_for_decision_task_on_non_existent_queue_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "non-existent-queue"}
    )
    resp.should.have.key("previousStartedEventId").equal(0)
    resp.should.have.key("startedEventId").equal(0)


# Has boto3 equivalent
@mock_swf_deprecated
def test_poll_for_decision_task_with_reverse_order():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue", reverse_order=True)
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        ["DecisionTaskStarted", "DecisionTaskScheduled", "WorkflowExecutionStarted"]
    )


@mock_swf
def test_poll_for_decision_task_with_reverse_order_boto3():
    client = setup_workflow_boto3()
    resp = client.poll_for_decision_task(
        domain="test-domain", taskList={"name": "queue"}, reverseOrder=True
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        ["DecisionTaskStarted", "DecisionTaskScheduled", "WorkflowExecutionStarted"]
    )


# CountPendingDecisionTasks endpoint
# Has boto3 equivalent
@mock_swf_deprecated
def test_count_pending_decision_tasks():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")
    resp = conn.count_pending_decision_tasks("test-domain", "queue")
    resp.should.equal({"count": 1, "truncated": False})


@mock_swf
def test_count_pending_decision_tasks_boto3():
    client = setup_workflow_boto3()
    client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})
    resp = client.count_pending_decision_tasks(
        domain="test-domain", taskList={"name": "queue"}
    )
    resp.should.have.key("count").equal(1)
    resp.should.have.key("truncated").equal(False)


# Has boto3 equivalent
@mock_swf_deprecated
def test_count_pending_decision_tasks_on_non_existent_task_list():
    conn = setup_workflow()
    resp = conn.count_pending_decision_tasks("test-domain", "non-existent")
    resp.should.equal({"count": 0, "truncated": False})


@mock_swf
def test_count_pending_decision_tasks_on_non_existent_task_list_boto3():
    client = setup_workflow_boto3()
    resp = client.count_pending_decision_tasks(
        domain="test-domain", taskList={"name": "non-existent"}
    )
    resp.should.have.key("count").equal(0)
    resp.should.have.key("truncated").equal(False)


# Has boto3 equivalent
@mock_swf_deprecated
def test_count_pending_decision_tasks_after_decision_completes():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    conn.respond_decision_task_completed(resp["taskToken"])

    resp = conn.count_pending_decision_tasks("test-domain", "queue")
    resp.should.equal({"count": 0, "truncated": False})


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
    resp.should.have.key("count").equal(0)
    resp.should.have.key("truncated").equal(False)


# RespondDecisionTaskCompleted endpoint
# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_no_decision():
    conn = setup_workflow()

    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    resp = conn.respond_decision_task_completed(
        task_token, execution_context="free-form context"
    )
    resp.should.be.none

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
        ]
    )
    evt = resp["events"][-1]
    evt["decisionTaskCompletedEventAttributes"].should.equal(
        {
            "executionContext": "free-form context",
            "scheduledEventId": 2,
            "startedEventId": 3,
        }
    )

    resp = conn.describe_workflow_execution("test-domain", conn.run_id, "uid-abcd1234")
    resp["latestExecutionContext"].should.equal("free-form context")


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
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
        ]
    )
    evt = resp["events"][-1]
    evt["decisionTaskCompletedEventAttributes"].should.equal(
        {
            "executionContext": "free-form context",
            "scheduledEventId": 2,
            "startedEventId": 3,
        }
    )

    resp = client.describe_workflow_execution(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    resp["latestExecutionContext"].should.equal("free-form context")


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_wrong_token():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")
    conn.respond_decision_task_completed.when.called_with(
        "not-a-correct-token"
    ).should.throw(SWFResponseError)


@mock_swf
def test_respond_decision_task_completed_with_wrong_token_boto3():
    client = setup_workflow_boto3()
    client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})
    with pytest.raises(ClientError) as ex:
        client.respond_decision_task_completed(taskToken="not-a-correct-token")
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal("Invalid token")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_on_close_workflow_execution():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    # bad: we're closing workflow execution manually, but endpoints are not
    # coded for now..
    wfe = swf_backend.domains[0].workflow_executions[-1]
    wfe.execution_status = "CLOSED"
    # /bad

    conn.respond_decision_task_completed.when.called_with(task_token).should.throw(
        SWFResponseError
    )


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
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId={}]".format(
            client.run_id
        )
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_task_already_completed():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]
    conn.respond_decision_task_completed(task_token)

    conn.respond_decision_task_completed.when.called_with(task_token).should.throw(
        SWFResponseError
    )


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
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown decision task, scheduledEventId = 2"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_complete_workflow_execution():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "CompleteWorkflowExecution",
            "completeWorkflowExecutionDecisionAttributes": {"result": "foo bar"},
        }
    ]
    resp = conn.respond_decision_task_completed(task_token, decisions=decisions)
    resp.should.be.none

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
            "WorkflowExecutionCompleted",
        ]
    )
    resp["events"][-1]["workflowExecutionCompletedEventAttributes"][
        "result"
    ].should.equal("foo bar")


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
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
            "WorkflowExecutionCompleted",
        ]
    )
    resp["events"][-1]["workflowExecutionCompletedEventAttributes"][
        "result"
    ].should.equal("foo bar")


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_close_decision_not_last():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        {"decisionType": "CompleteWorkflowExecution"},
        {"decisionType": "WeDontCare"},
    ]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
    ).should.throw(SWFResponseError, r"Close must be last decision in list")


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
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.equal(
        "Close must be last decision in list"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_invalid_decision_type():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        {"decisionType": "BadDecisionType"},
        {"decisionType": "CompleteWorkflowExecution"},
    ]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
    ).should.throw(
        SWFResponseError,
        r"Value 'BadDecisionType' at 'decisions.1.member.decisionType'",
    )


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
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.match(
        "Value 'BadDecisionType' at 'decisions.1.member.decisionType'"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_missing_attributes():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "should trigger even with incorrect decision type",
            "startTimerDecisionAttributes": {},
        }
    ]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
    ).should.throw(
        SWFResponseError,
        r"Value null at 'decisions.1.member.startTimerDecisionAttributes.timerId' "
        r"failed to satisfy constraint: Member must not be null",
    )


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_missing_attributes_totally():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [{"decisionType": "StartTimer"}]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
    ).should.throw(
        SWFResponseError,
        r"Value null at 'decisions.1.member.startTimerDecisionAttributes.timerId' "
        r"failed to satisfy constraint: Member must not be null",
    )


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
    ex.value.response["Error"]["Code"].should.equal("ValidationException")
    ex.value.response["Error"]["Message"].should.match(
        "Value null at 'decisions.1.member.startTimerDecisionAttributes.timerId' failed to satisfy constraint"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# Has boto3 equivalent
@mock_swf_deprecated
def test_respond_decision_task_completed_with_fail_workflow_execution():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
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
    resp = conn.respond_decision_task_completed(task_token, decisions=decisions)
    resp.should.be.none

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
            "WorkflowExecutionFailed",
        ]
    )
    attrs = resp["events"][-1]["workflowExecutionFailedEventAttributes"]
    attrs["reason"].should.equal("my rules")
    attrs["details"].should.equal("foo")


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
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
            "WorkflowExecutionFailed",
        ]
    )
    attrs = resp["events"][-1]["workflowExecutionFailedEventAttributes"]
    attrs["reason"].should.equal("my rules")
    attrs["details"].should.equal("foo")


# Has boto3 equivalent
@mock_swf_deprecated
@freeze_time("2015-01-01 12:00:00")
def test_respond_decision_task_completed_with_schedule_activity_task():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
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
    resp = conn.respond_decision_task_completed(task_token, decisions=decisions)
    resp.should.be.none

    resp = conn.get_workflow_execution_history(
        "test-domain", conn.run_id, "uid-abcd1234"
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
            "ActivityTaskScheduled",
        ]
    )
    resp["events"][-1]["activityTaskScheduledEventAttributes"].should.equal(
        {
            "decisionTaskCompletedEventId": 4,
            "activityId": "my-activity-001",
            "activityType": {"name": "test-activity", "version": "v1.1"},
            "heartbeatTimeout": "60",
            "input": "123",
            "taskList": {"name": "my-task-list"},
        }
    )

    resp = conn.describe_workflow_execution("test-domain", conn.run_id, "uid-abcd1234")
    resp["latestActivityTaskTimestamp"].should.equal(1420113600.0)


@mock_swf
@freeze_time("2015-01-01 12:00:00")
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
    types.should.equal(
        [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskCompleted",
            "ActivityTaskScheduled",
        ]
    )
    resp["events"][-1]["activityTaskScheduledEventAttributes"].should.equal(
        {
            "decisionTaskCompletedEventId": 4,
            "activityId": "my-activity-001",
            "activityType": {"name": "test-activity", "version": "v1.1"},
            "heartbeatTimeout": "60",
            "input": "123",
            "taskList": {"name": "my-task-list"},
        }
    )

    resp = client.describe_workflow_execution(
        domain="test-domain",
        execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
    )
    resp["latestActivityTaskTimestamp"].should.be.a(datetime)
    if not settings.TEST_SERVER_MODE:
        ts = resp["latestActivityTaskTimestamp"].strftime("%Y-%m-%d %H:%M:%S")
        ts.should.equal("2015-01-01 12:00:00")
