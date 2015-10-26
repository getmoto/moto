import boto
from sure import expect

from moto import mock_swf
from moto.swf.exceptions import SWFUnknownResourceFault

from ..utils import setup_workflow


# PollForActivityTask endpoint
@mock_swf
def test_poll_for_activity_task_when_one():
    conn = setup_workflow()
    decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
    conn.respond_decision_task_completed(decision_token, decisions=[
        {
            "decisionType": "ScheduleActivityTask",
            "scheduleActivityTaskDecisionAttributes": {
                "activityId": "my-activity-001",
                "activityType": { "name": "test-activity", "version": "v1.1" },
                "taskList": { "name": "activity-task-list" },
            }
        }
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

