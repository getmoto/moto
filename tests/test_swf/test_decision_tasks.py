import boto
from sure import expect

from moto import mock_swf
from moto.swf.exceptions import (
    SWFUnknownResourceFault,
)

from .utils import mock_basic_workflow_type


@mock_swf
def setup_workflow():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn = mock_basic_workflow_type("test-domain", conn)
    conn.register_activity_type("test-domain", "test-activity", "v1.1")
    wfe = conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    conn.run_id = wfe["runId"]
    return conn


# PollForDecisionTask endpoint
@mock_swf
def test_poll_for_decision_task_when_one():
    conn = setup_workflow()

    resp = conn.get_workflow_execution_history("test-domain", conn.run_id, "uid-abcd1234")
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])

    resp = conn.poll_for_decision_task("test-domain", "queue", identity="srv01")
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled", "DecisionTaskStarted"])

    resp["events"][-1]["decisionTaskStartedEventAttributes"]["identity"].should.equal("srv01")

@mock_swf
def test_poll_for_decision_task_when_none():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")

    resp = conn.poll_for_decision_task("test-domain", "queue")
    # this is the DecisionTask representation you get from the real SWF
    # after waiting 60s when there's no decision to be taken
    resp.should.equal({"previousStartedEventId": 0, "startedEventId": 0})

@mock_swf
def test_poll_for_decision_task_with_reverse_order():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue", reverse_order=True)
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["DecisionTaskStarted", "DecisionTaskScheduled", "WorkflowExecutionStarted"])
