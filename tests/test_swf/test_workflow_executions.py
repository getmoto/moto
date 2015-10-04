import boto
from nose.tools import assert_raises
from sure import expect

from moto import mock_swf
from moto.swf.exceptions import (
    SWFWorkflowExecutionAlreadyStartedFault,
    SWFTypeDeprecatedFault,
    SWFUnknownResourceFault,
)


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

    with assert_raises(SWFWorkflowExecutionAlreadyStartedFault) as err:
        conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("WorkflowExecutionAlreadyStartedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#WorkflowExecutionAlreadyStartedFault",
    })

@mock_swf
def test_start_workflow_execution_on_deprecated_type():
    conn = setup_swf_environment()
    conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    with assert_raises(SWFTypeDeprecatedFault) as err:
        conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("TypeDeprecatedFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#TypeDeprecatedFault",
        "message": "WorkflowType=[name=test-workflow, version=v1.0]"
    })


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

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.describe_workflow_execution("test-domain", "wrong-run-id", "wrong-workflow-id")

    ex = err.exception
    ex.status.should.equal(400)
    ex.error_code.should.equal("UnknownResourceFault")
    ex.body.should.equal({
        "__type": "com.amazonaws.swf.base.model#UnknownResourceFault",
        "message": "Unknown execution: WorkflowExecution=[workflowId=wrong-workflow-id, runId=wrong-run-id]"
    })


# GetWorkflowExecutionHistory endpoint
@mock_swf
def test_get_workflow_execution_history():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution("test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    resp = conn.get_workflow_execution_history("test-domain", run_id, "uid-abcd1234")
    resp["events"].should.be.a("list")
    evt = resp["events"][0]
    evt["eventType"].should.equal("WorkflowExecutionStarted")


@mock_swf
def test_get_workflow_execution_history_on_non_existent_workflow_execution():
    conn = setup_swf_environment()

    with assert_raises(SWFUnknownResourceFault) as err:
        conn.get_workflow_execution_history("test-domain", "wrong-run-id", "wrong-workflow-id")

    # (the rest is already tested above)
