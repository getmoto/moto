from datetime import datetime
from unittest import SkipTest

from dateutil.parser import parse as dtparse
from freezegun import freeze_time

from moto import mock_swf, settings

from ..utils import SCHEDULE_ACTIVITY_TASK_DECISION
from ..utils import setup_workflow_boto3


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

    with freeze_time("2015-01-01 12:04:30 UTC"):
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )
        assert resp["events"][-1]["eventType"] == "ActivityTaskStarted"

    with freeze_time("2015-01-01 12:05:30 UTC"):
        # => Activity Task Heartbeat timeout reached!!
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        assert resp["events"][-2]["eventType"] == "ActivityTaskTimedOut"
        attrs = resp["events"][-2]["activityTaskTimedOutEventAttributes"]
        assert attrs["timeoutType"] == "HEARTBEAT"
        # checks that event has been emitted at 12:05:00, not 12:05:30
        assert isinstance(resp["events"][-2]["eventTimestamp"], datetime)
        ts = resp["events"][-2]["eventTimestamp"]
        assert ts == dtparse("2015-01-01 12:05:00 UTC")


# Decision Task Start to Close timeout
# Default value in workflow helpers: 5 mins
@mock_swf
def test_decision_task_start_to_close_timeout_boto3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to manipulate time in ServerMode")

    with freeze_time("2015-01-01 12:00:00 UTC"):
        client = setup_workflow_boto3()
        client.poll_for_decision_task(domain="test-domain", taskList={"name": "queue"})

    with freeze_time("2015-01-01 12:04:30 UTC"):
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        assert event_types == [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
        ]

    with freeze_time("2015-01-01 12:05:30 UTC"):
        # => Decision Task Start to Close timeout reached!!
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        assert event_types == [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "DecisionTaskStarted",
            "DecisionTaskTimedOut",
            "DecisionTaskScheduled",
        ]
        attrs = resp["events"][-2]["decisionTaskTimedOutEventAttributes"]
        assert attrs == {
            "scheduledEventId": 2,
            "startedEventId": 3,
            "timeoutType": "START_TO_CLOSE",
        }
        # checks that event has been emitted at 12:05:00, not 12:05:30
        assert isinstance(resp["events"][-2]["eventTimestamp"], datetime)
        ts = resp["events"][-2]["eventTimestamp"]
        assert ts == dtparse("2015-01-01 12:05:00 UTC")


# Workflow Execution Start to Close timeout
# Default value in workflow helpers: 2 hours
@mock_swf
def test_workflow_execution_start_to_close_timeout_boto3():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to manipulate time in ServerMode")
    with freeze_time("2015-01-01 12:00:00 UTC"):
        client = setup_workflow_boto3()

    with freeze_time("2015-01-01 13:59:30 UTC"):
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        assert event_types == ["WorkflowExecutionStarted", "DecisionTaskScheduled"]

    with freeze_time("2015-01-01 14:00:30 UTC"):
        # => Workflow Execution Start to Close timeout reached!!
        resp = client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": client.run_id, "workflowId": "uid-abcd1234"},
        )

        event_types = [evt["eventType"] for evt in resp["events"]]
        assert event_types == [
            "WorkflowExecutionStarted",
            "DecisionTaskScheduled",
            "WorkflowExecutionTimedOut",
        ]
        attrs = resp["events"][-1]["workflowExecutionTimedOutEventAttributes"]
        assert attrs == {"childPolicy": "ABANDON", "timeoutType": "START_TO_CLOSE"}
        # checks that event has been emitted at 14:00:00, not 14:00:30
        assert isinstance(resp["events"][-1]["eventTimestamp"], datetime)
        ts = resp["events"][-1]["eventTimestamp"]
        assert ts == dtparse("2015-01-01 14:00:00 UTC")
