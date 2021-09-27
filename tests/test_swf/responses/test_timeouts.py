from datetime import datetime
from freezegun import freeze_time
from unittest import SkipTest
import sure  # noqa

from moto import mock_swf_deprecated, mock_swf, settings

from ..utils import setup_workflow, SCHEDULE_ACTIVITY_TASK_DECISION
from ..utils import setup_workflow_boto3


# Activity Task Heartbeat timeout
# Default value in workflow helpers: 5 mins
# Has boto3 equivalent
@mock_swf_deprecated
def test_activity_task_heartbeat_timeout():
    with freeze_time("2015-01-01 12:00:00"):
        conn = setup_workflow()
        decision_token = conn.poll_for_decision_task("test-domain", "queue")[
            "taskToken"
        ]
        conn.respond_decision_task_completed(
            decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
        )
        conn.poll_for_activity_task(
            "test-domain", "activity-task-list", identity="surprise"
        )

    with freeze_time("2015-01-01 12:04:30"):
        resp = conn.get_workflow_execution_history(
            "test-domain", conn.run_id, "uid-abcd1234"
        )
        resp["events"][-1]["eventType"].should.equal("ActivityTaskStarted")

    with freeze_time("2015-01-01 12:05:30"):
        # => Activity Task Heartbeat timeout reached!!
        resp = conn.get_workflow_execution_history(
            "test-domain", conn.run_id, "uid-abcd1234"
        )

        resp["events"][-2]["eventType"].should.equal("ActivityTaskTimedOut")
        attrs = resp["events"][-2]["activityTaskTimedOutEventAttributes"]
        attrs["timeoutType"].should.equal("HEARTBEAT")
        # checks that event has been emitted at 12:05:00, not 12:05:30
        resp["events"][-2]["eventTimestamp"].should.equal(1420113900.0)

        resp["events"][-1]["eventType"].should.equal("DecisionTaskScheduled")


# Activity Task Heartbeat timeout
# Default value in workflow helpers: 5 mins
@mock_swf
def test_activity_task_heartbeat_timeout_boto3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to manipulate time in ServerMode")
    with freeze_time("2015-01-01 12:00:00"):
        client = setup_workflow_boto3()
        decision_token = client.poll_for_decision_task(
            domain="test-domain", taskList={"name": "queue"}
        )["taskToken"]
        client.respond_decision_task_completed(
            taskToken=decision_token, decisions=[SCHEDULE_ACTIVITY_TASK_DECISION]
        )
        client.poll_for_activity_task(
            domain="test-domain",
            taskList={"name": "activity-task-list"},
            identity="surprise",
        )

    with freeze_time("2015-01-01 12:04:30"):
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )
        resp["events"][-1]["eventType"].should.equal("ActivityTaskStarted")

    with freeze_time("2015-01-01 12:05:30"):
        # => Activity Task Heartbeat timeout reached!!
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        resp["events"][-2]["eventType"].should.equal("ActivityTaskTimedOut")
        attrs = resp["events"][-2]["activityTaskTimedOutEventAttributes"]
        attrs["timeoutType"].should.equal("HEARTBEAT")
        # checks that event has been emitted at 12:05:00, not 12:05:30
        resp["events"][-2]["eventTimestamp"].should.be.a(datetime)
        ts = resp["events"][-2]["eventTimestamp"].strftime("%Y-%m-%d %H:%M:%S")
        ts.should.equal("2015-01-01 12:05:00")


# Decision Task Start to Close timeout
# Default value in workflow helpers: 5 mins
# Has boto3 equivalent
@mock_swf_deprecated
def test_decision_task_start_to_close_timeout():
    pass
    with freeze_time("2015-01-01 12:00:00"):
        conn = setup_workflow()
        conn.poll_for_decision_task("test-domain", "queue")["taskToken"]

    with freeze_time("2015-01-01 12:04:30"):
        resp = conn.get_workflow_execution_history(
            "test-domain", conn.run_id, "uid-abcd1234"
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(
            ["WorkflowExecutionStarted", "DecisionTaskScheduled", "DecisionTaskStarted"]
        )

    with freeze_time("2015-01-01 12:05:30"):
        # => Decision Task Start to Close timeout reached!!
        resp = conn.get_workflow_execution_history(
            "test-domain", conn.run_id, "uid-abcd1234"
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(
            [
                "WorkflowExecutionStarted",
                "DecisionTaskScheduled",
                "DecisionTaskStarted",
                "DecisionTaskTimedOut",
                "DecisionTaskScheduled",
            ]
        )
        attrs = resp["events"][-2]["decisionTaskTimedOutEventAttributes"]
        attrs.should.equal(
            {
                "scheduledEventId": 2,
                "startedEventId": 3,
                "timeoutType": "START_TO_CLOSE",
            }
        )
        # checks that event has been emitted at 12:05:00, not 12:05:30
        resp["events"][-2]["eventTimestamp"].should.equal(1420113900.0)


# Decision Task Start to Close timeout
# Default value in workflow helpers: 5 mins
@mock_swf
def test_decision_task_start_to_close_timeout_boto3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to manipulate time in ServerMode")

    with freeze_time("2015-01-01 12:00:00"):
        client = setup_workflow_boto3()
        client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})

    with freeze_time("2015-01-01 12:04:30"):
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(
            ["WorkflowExecutionStarted", "DecisionTaskScheduled", "DecisionTaskStarted"]
        )

    with freeze_time("2015-01-01 12:05:30"):
        # => Decision Task Start to Close timeout reached!!
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(
            [
                "WorkflowExecutionStarted",
                "DecisionTaskScheduled",
                "DecisionTaskStarted",
                "DecisionTaskTimedOut",
                "DecisionTaskScheduled",
            ]
        )
        attrs = resp["events"][-2]["decisionTaskTimedOutEventAttributes"]
        attrs.should.equal(
            {
                "scheduledEventId": 2,
                "startedEventId": 3,
                "timeoutType": "START_TO_CLOSE",
            }
        )
        # checks that event has been emitted at 12:05:00, not 12:05:30
        resp["events"][-2]["eventTimestamp"].should.be.a(datetime)
        ts = resp["events"][-2]["eventTimestamp"].strftime("%Y-%m-%d %H:%M:%S")
        ts.should.equal("2015-01-01 12:05:00")


# Workflow Execution Start to Close timeout
# Default value in workflow helpers: 2 hours
# Has boto3 equivalent
@mock_swf_deprecated
def test_workflow_execution_start_to_close_timeout():
    pass
    with freeze_time("2015-01-01 12:00:00"):
        conn = setup_workflow()

    with freeze_time("2015-01-01 13:59:30"):
        resp = conn.get_workflow_execution_history(
            "test-domain", conn.run_id, "uid-abcd1234"
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])

    with freeze_time("2015-01-01 14:00:30"):
        # => Workflow Execution Start to Close timeout reached!!
        resp = conn.get_workflow_execution_history(
            "test-domain", conn.run_id, "uid-abcd1234"
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(
            [
                "WorkflowExecutionStarted",
                "DecisionTaskScheduled",
                "WorkflowExecutionTimedOut",
            ]
        )
        attrs = resp["events"][-1]["workflowExecutionTimedOutEventAttributes"]
        attrs.should.equal({"childPolicy": "ABANDON", "timeoutType": "START_TO_CLOSE"})
        # checks that event has been emitted at 14:00:00, not 14:00:30
        resp["events"][-1]["eventTimestamp"].should.equal(1420120800.0)


# Workflow Execution Start to Close timeout
# Default value in workflow helpers: 2 hours
@mock_swf
def test_workflow_execution_start_to_close_timeout_boto3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to manipulate time in ServerMode")
    with freeze_time("2015-01-01 12:00:00"):
        client = setup_workflow_boto3()

    with freeze_time("2015-01-01 13:59:30"):
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])

    with freeze_time("2015-01-01 14:00:30"):
        # => Workflow Execution Start to Close timeout reached!!
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        event_types.should.equal(
            [
                "WorkflowExecutionStarted",
                "DecisionTaskScheduled",
                "WorkflowExecutionTimedOut",
            ]
        )
        attrs = resp["events"][-1]["workflowExecutionTimedOutEventAttributes"]
        attrs.should.equal({"childPolicy": "ABANDON", "timeoutType": "START_TO_CLOSE"})
        # checks that event has been emitted at 14:00:00, not 14:00:30
        resp["events"][-1]["eventTimestamp"].should.be.a(datetime)
        ts = resp["events"][-1]["eventTimestamp"].strftime("%Y-%m-%d %H:%M:%S")
        ts.should.equal("2015-01-01 14:00:00")
