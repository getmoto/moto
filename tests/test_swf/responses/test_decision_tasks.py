from boto.swf.exceptions import SWFResponseError
from freezegun import freeze_time
import sure  # noqa

from moto import mock_swf_deprecated
from moto.swf import swf_backend

from ..utils import setup_workflow


# PollForDecisionTask endpoint
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


@mock_swf_deprecated
def test_poll_for_decision_task_when_none():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")

    resp = conn.poll_for_decision_task("test-domain", "queue")
    # this is the DecisionTask representation you get from the real SWF
    # after waiting 60s when there's no decision to be taken
    resp.should.equal(
        {"previousStartedEventId": 0, "startedEventId": 0, "taskToken": ""}
    )


@mock_swf_deprecated
def test_poll_for_decision_task_on_non_existent_queue():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "non-existent-queue")
    resp.should.equal(
        {"previousStartedEventId": 0, "startedEventId": 0, "taskToken": ""}
    )


@mock_swf_deprecated
def test_poll_for_decision_task_with_reverse_order():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue", reverse_order=True)
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(
        ["DecisionTaskStarted", "DecisionTaskScheduled", "WorkflowExecutionStarted"]
    )


# CountPendingDecisionTasks endpoint
@mock_swf_deprecated
def test_count_pending_decision_tasks():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")
    resp = conn.count_pending_decision_tasks("test-domain", "queue")
    resp.should.equal({"count": 1, "truncated": False})


@mock_swf_deprecated
def test_count_pending_decision_tasks_on_non_existent_task_list():
    conn = setup_workflow()
    resp = conn.count_pending_decision_tasks("test-domain", "non-existent")
    resp.should.equal({"count": 0, "truncated": False})


@mock_swf_deprecated
def test_count_pending_decision_tasks_after_decision_completes():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    conn.respond_decision_task_completed(resp["taskToken"])

    resp = conn.count_pending_decision_tasks("test-domain", "queue")
    resp.should.equal({"count": 0, "truncated": False})


# RespondDecisionTaskCompleted endpoint
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


@mock_swf_deprecated
def test_respond_decision_task_completed_with_wrong_token():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")
    conn.respond_decision_task_completed.when.called_with(
        "not-a-correct-token"
    ).should.throw(SWFResponseError)


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


@mock_swf_deprecated
def test_respond_decision_task_completed_with_task_already_completed():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]
    conn.respond_decision_task_completed(task_token)

    conn.respond_decision_task_completed.when.called_with(task_token).should.throw(
        SWFResponseError
    )


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
