import boto
from sure import expect

from moto import mock_swf
from moto.swf import swf_backend
from moto.swf.exceptions import (
    SWFValidationException,
    SWFUnknownResourceFault,
)

from ..utils import setup_workflow


SCHEDULE_ACTIVITY_TASK_DECISION = {
    "decisionType": "ScheduleActivityTask",
    "scheduleActivityTaskDecisionAttributes": {
        "activityId": "my-activity-001",
        "activityType": { "name": "test-activity", "version": "v1.1" },
        "taskList": { "name": "activity-task-list" },
    }
}

# PollForActivityTask endpoint
@mock_swf
def test_poll_for_activity_task_when_one():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(decision_token, decisions=[
        SCHEDULE_ACTIVITY_TASK_DECISION
    ])
    resp = conn.poll_for_activity_task("test-domain", "activity-task-list", identity="surprise")
    resp["activityId"].should.equal("my-activity-001")
    resp["taskToken"].should_not.be.none

    resp = conn.get_workflow_execution_history("test-domain", conn.run_id, "uid-abcd1234")
    resp["events"][-1]["eventType"].should.equal("ActivityTaskStarted")
    resp["events"][-1]["activityTaskStartedEventAttributes"].should.equal(
        { "identity": "surprise", "scheduledEventId": 5 }
    )

@mock_swf
def test_poll_for_activity_task_when_none():
    conn = setup_workflow()
    resp = conn.poll_for_activity_task("test-domain", "activity-task-list")
    resp.should.equal({"startedEventId": 0})

@mock_swf
def test_poll_for_activity_task_on_non_existent_queue():
    conn = setup_workflow()
    resp = conn.poll_for_activity_task("test-domain", "non-existent-queue")
    resp.should.equal({"startedEventId": 0})


# CountPendingActivityTasks endpoint
@mock_swf
def test_count_pending_activity_tasks():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(decision_token, decisions=[
        SCHEDULE_ACTIVITY_TASK_DECISION
    ])

    resp = conn.count_pending_activity_tasks("test-domain", "activity-task-list")
    resp.should.equal({"count": 1, "truncated": False})

@mock_swf
def test_count_pending_decision_tasks_on_non_existent_task_list():
    conn = setup_workflow()
    resp = conn.count_pending_activity_tasks("test-domain", "non-existent")
    resp.should.equal({"count": 0, "truncated": False})


# RespondActivityTaskCompleted endpoint
@mock_swf
def test_poll_for_activity_task_when_one():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(decision_token, decisions=[
        SCHEDULE_ACTIVITY_TASK_DECISION
    ])
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")["taskToken"]

    resp = conn.respond_activity_task_completed(activity_token, result="result of the task")
    resp.should.be.none

    resp = conn.get_workflow_execution_history("test-domain", conn.run_id, "uid-abcd1234")
    resp["events"][-2]["eventType"].should.equal("ActivityTaskCompleted")
    resp["events"][-2]["activityTaskCompletedEventAttributes"].should.equal(
        { "result": "result of the task", "scheduledEventId": 5, "startedEventId": 6 }
    )

@mock_swf
def test_respond_activity_task_completed_with_wrong_token():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(decision_token, decisions=[
        SCHEDULE_ACTIVITY_TASK_DECISION
    ])
    conn.poll_for_activity_task("test-domain", "activity-task-list")
    conn.respond_activity_task_completed.when.called_with(
        "not-a-correct-token"
    ).should.throw(SWFValidationException, "Invalid token")

@mock_swf
def test_respond_activity_task_completed_on_closed_workflow_execution():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(decision_token, decisions=[
        SCHEDULE_ACTIVITY_TASK_DECISION
    ])
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")["taskToken"]

    # bad: we're closing workflow execution manually, but endpoints are not coded for now..
    wfe = swf_backend.domains[0].workflow_executions.values()[0]
    wfe.execution_status = "CLOSED"
    # /bad

    conn.respond_activity_task_completed.when.called_with(
        activity_token
    ).should.throw(SWFUnknownResourceFault, "WorkflowExecution=")

@mock_swf
def test_respond_activity_task_completed_with_task_already_completed():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(decision_token, decisions=[
        SCHEDULE_ACTIVITY_TASK_DECISION
    ])
    activity_token = conn.poll_for_activity_task("test-domain", "activity-task-list")["taskToken"]

    conn.respond_activity_task_completed(activity_token)

    conn.respond_activity_task_completed.when.called_with(
        activity_token
    ).should.throw(SWFUnknownResourceFault, "Unknown activity, scheduledEventId = 5")
