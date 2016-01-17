import boto
from boto.swf.exceptions import SWFResponseError

# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # noqa
from nose.tools import assert_raises
from sure import expect

from moto import mock_swf


# Utils
@mock_swf
def setup_swf_environment():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.register_workflow_type(
        "test-domain", "test-workflow", "v1.0",
        task_list="queue", default_child_policy="TERMINATE",
        default_execution_start_to_close_timeout="300",
        default_task_start_to_close_timeout="300",
    )
    conn.register_activity_type("test-domain", "test-activity", "v1.1")
    return conn


# StartWorkflowExecution endpoint
@mock_swf
def test_start_workflow_execution():
    conn = setup_swf_environment()

    wf = conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    wf.should.contain("runId")

@mock_swf
def test_start_already_started_workflow_execution():
    conn = setup_swf_environment()
    conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")

    conn.start_workflow_execution.when.called_with(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    ).should.throw(SWFResponseError)

@mock_swf
def test_start_workflow_execution_on_deprecated_type():
    conn = setup_swf_environment()
    conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    conn.start_workflow_execution.when.called_with(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    ).should.throw(SWFResponseError)


# DescribeWorkflowExecution endpoint
@mock_swf
def test_describe_workflow_execution():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    wfe = conn.describe_workflow_execution("test-domain", run_id, "uid-abcd1234")
    wfe["executionInfo"]["execution"]["workflowId"].should.equal("uid-abcd1234")
    wfe["executionInfo"]["executionStatus"].should.equal("OPEN")

@mock_swf
def test_describe_non_existent_workflow_execution():
    conn = setup_swf_environment()

    conn.describe_workflow_execution.when.called_with(
        "test-domain", "wrong-run-id", "wrong-workflow-id"
    ).should.throw(SWFResponseError)


# GetWorkflowExecutionHistory endpoint
@mock_swf
def test_get_workflow_execution_history():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    resp = conn.get_workflow_execution_history("test-domain", run_id, "uid-abcd1234")
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])

@mock_swf
def test_get_workflow_execution_history_with_reverse_order():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    resp = conn.get_workflow_execution_history("test-domain", run_id, "uid-abcd1234",
                                               reverse_order=True)
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["DecisionTaskScheduled", "WorkflowExecutionStarted"])

@mock_swf
def test_get_workflow_execution_history_on_non_existent_workflow_execution():
    conn = setup_swf_environment()

    conn.get_workflow_execution_history.when.called_with(
        "test-domain", "wrong-run-id", "wrong-workflow-id"
    ).should.throw(SWFResponseError)


# TerminateWorkflowExecution endpoint
@mock_swf
def test_terminate_workflow_execution():
    conn = setup_swf_environment()
    run_id = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    )["runId"]

    resp = conn.terminate_workflow_execution("test-domain", "uid-abcd1234",
                                             details="some details",
                                             reason="a more complete reason",
                                             run_id=run_id)
    resp.should.be.none

    resp = conn.get_workflow_execution_history("test-domain", run_id, "uid-abcd1234")
    evt = resp["events"][-1]
    evt["eventType"].should.equal("WorkflowExecutionTerminated")
    attrs = evt["workflowExecutionTerminatedEventAttributes"]
    attrs["details"].should.equal("some details")
    attrs["reason"].should.equal("a more complete reason")
    attrs["cause"].should.equal("OPERATOR_INITIATED")

@mock_swf
def test_terminate_workflow_execution_with_wrong_workflow_or_run_id():
    conn = setup_swf_environment()
    run_id = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    )["runId"]

    # terminate workflow execution
    resp = conn.terminate_workflow_execution("test-domain", "uid-abcd1234")

    # already closed, with run_id
    conn.terminate_workflow_execution.when.called_with(
        "test-domain", "uid-abcd1234", run_id=run_id
    ).should.throw(
        SWFResponseError, "WorkflowExecution=[workflowId=uid-abcd1234, runId="
    )

    # already closed, without run_id
    conn.terminate_workflow_execution.when.called_with(
        "test-domain", "uid-abcd1234"
    ).should.throw(
        SWFResponseError, "Unknown execution, workflowId = uid-abcd1234"
    )

    # wrong workflow id
    conn.terminate_workflow_execution.when.called_with(
        "test-domain", "uid-non-existent"
    ).should.throw(
        SWFResponseError, "Unknown execution, workflowId = uid-non-existent"
    )

    # wrong run_id
    conn.terminate_workflow_execution.when.called_with(
        "test-domain", "uid-abcd1234", run_id="foo"
    ).should.throw(
        SWFResponseError, "WorkflowExecution=[workflowId=uid-abcd1234, runId="
    )
