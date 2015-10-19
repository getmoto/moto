import boto
from sure import expect

from moto import mock_swf
from moto.swf import swf_backend
from moto.swf.exceptions import (
    SWFUnknownResourceFault,
    SWFValidationException,
    SWFDecisionValidationException,
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
def test_poll_for_decision_task_on_non_existent_queue():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "non-existent-queue")
    resp.should.equal({"previousStartedEventId": 0, "startedEventId": 0})

@mock_swf
def test_poll_for_decision_task_with_reverse_order():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue", reverse_order=True)
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["DecisionTaskStarted", "DecisionTaskScheduled", "WorkflowExecutionStarted"])


# CountPendingDecisionTasks endpoint
@mock_swf
def test_count_pending_decision_tasks():
    conn = setup_workflow()
    conn.poll_for_decision_task("test-domain", "queue")
    resp = conn.count_pending_decision_tasks("test-domain", "queue")
    resp.should.equal({"count": 1, "truncated": False})

@mock_swf
def test_count_pending_decision_tasks_on_non_existent_task_list():
    conn = setup_workflow()
    resp = conn.count_pending_decision_tasks("test-domain", "non-existent")
    resp.should.equal({"count": 0, "truncated": False})


# RespondDecisionTaskCompleted endpoint
@mock_swf
def test_respond_decision_task_completed_with_no_decision():
    conn = setup_workflow()

    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    resp = conn.respond_decision_task_completed(task_token)
    resp.should.be.none

    resp = conn.get_workflow_execution_history("test-domain", conn.run_id, "uid-abcd1234")
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal([
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
    ])
    evt = resp["events"][-1]
    evt["decisionTaskCompletedEventAttributes"].should.equal({
        "scheduledEventId": 2,
        "startedEventId": 3,
    })

@mock_swf
def test_respond_decision_task_completed_with_wrong_token():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    conn.respond_decision_task_completed.when.called_with(
        "not-a-correct-token"
    ).should.throw(SWFValidationException)

@mock_swf
def test_respond_decision_task_completed_on_close_workflow_execution():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    # bad: we're closing workflow execution manually, but endpoints are not coded for now..
    wfe = swf_backend.domains[0].workflow_executions.values()[0]
    wfe.execution_status = "CLOSED"
    # /bad

    conn.respond_decision_task_completed.when.called_with(
        task_token
    ).should.throw(SWFUnknownResourceFault)

@mock_swf
def test_respond_decision_task_completed_with_task_already_completed():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]
    conn.respond_decision_task_completed(task_token)

    conn.respond_decision_task_completed.when.called_with(
        task_token
    ).should.throw(SWFUnknownResourceFault)

@mock_swf
def test_respond_decision_task_completed_with_complete_workflow_execution():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [{
        "decisionType": "CompleteWorkflowExecution",
        "completeWorkflowExecutionEventAttributes": {}
    }]
    resp = conn.respond_decision_task_completed(task_token, decisions=decisions)
    resp.should.be.none

    resp = conn.get_workflow_execution_history("test-domain", conn.run_id, "uid-abcd1234")
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal([
        "WorkflowExecutionStarted",
        "DecisionTaskScheduled",
        "DecisionTaskStarted",
        "DecisionTaskCompleted",
        "WorkflowExecutionCompleted",
    ])

@mock_swf
def test_respond_decision_task_completed_with_close_decision_not_last():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        { "decisionType": "CompleteWorkflowExecution" },
        { "decisionType": "WeDontCare" },
    ]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
    ).should.throw(SWFValidationException, r"Close must be last decision in list")

@mock_swf
def test_respond_decision_task_completed_with_invalid_decision_type():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        { "decisionType": "BadDecisionType" },
        { "decisionType": "CompleteWorkflowExecution" },
    ]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
        ).should.throw(
            SWFDecisionValidationException,
            r"Value 'BadDecisionType' at 'decisions.1.member.decisionType'"
        )

@mock_swf
def test_respond_decision_task_completed_with_missing_attributes():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        {
            "decisionType": "should trigger even with incorrect decision type",
            "startTimerDecisionAttributes": {}
        },
    ]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
        ).should.throw(
            SWFDecisionValidationException,
            r"Value null at 'decisions.1.member.startTimerDecisionAttributes.timerId' " \
            r"failed to satisfy constraint: Member must not be null"
        )

@mock_swf
def test_respond_decision_task_completed_with_missing_attributes_totally():
    conn = setup_workflow()
    resp = conn.poll_for_decision_task("test-domain", "queue")
    task_token = resp["taskToken"]

    decisions = [
        { "decisionType": "StartTimer" },
    ]

    conn.respond_decision_task_completed.when.called_with(
        task_token, decisions=decisions
        ).should.throw(
            SWFDecisionValidationException,
            r"Value null at 'decisions.1.member.startTimerDecisionAttributes.timerId' " \
            r"failed to satisfy constraint: Member must not be null"
        )
