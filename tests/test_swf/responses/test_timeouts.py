import boto
from freezegun import freeze_time
from sure import expect

from moto import mock_swf

from ..utils import setup_workflow, SCHEDULE_ACTIVITY_TASK_DECISION


# Activity Task Heartbeat timeout
# Default value in workflow helpers: 5 mins
@mock_swf
def test_activity_task_heartbeat_timeout():
    with freeze_time("2015-01-01 12:00:00"):
        conn = setup_workflow()
        decision_token = conn.poll_for_decision_task("test-domain", "queue")["taskToken"]
        conn.respond_decision_task_completed(decision_token, decisions=[
            SCHEDULE_ACTIVITY_TASK_DECISION
        ])
        conn.poll_for_activity_task("test-domain", "activity-task-list", identity="surprise")

    with freeze_time("2015-01-01 12:04:30"):
        resp = conn.get_workflow_execution_history("test-domain", conn.run_id, "uid-abcd1234")
        resp["events"][-1]["eventType"].should.equal("ActivityTaskStarted")

    with freeze_time("2015-01-01 12:05:30"):
        # => Activity Task Heartbeat timeout reached!!
        resp = conn.get_workflow_execution_history("test-domain", conn.run_id, "uid-abcd1234")

        resp["events"][-2]["eventType"].should.equal("ActivityTaskTimedOut")
        attrs = resp["events"][-2]["activityTaskTimedOutEventAttributes"]
        attrs["timeoutType"].should.equal("HEARTBEAT")

        resp["events"][-1]["eventType"].should.equal("DecisionTaskScheduled")
