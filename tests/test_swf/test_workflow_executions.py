import boto
from nose.tools import assert_raises
from sure import expect

from moto import mock_swf
from moto.swf.exceptions import (
    SWFWorkflowExecutionAlreadyStartedFault,
    SWFTypeDeprecatedFault,
)


# Utils
@mock_swf
def setup_swf_environment():
    conn = boto.connect_swf("the_key", "the_secret")
    conn.register_domain("test-domain", "60", description="A test domain")
    conn.register_workflow_type("test-domain", "test-workflow", "v1.0")
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
