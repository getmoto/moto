import boto
from boto.swf.exceptions import SWFResponseError
from datetime import datetime, timedelta

import sure  # noqa
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # noqa

from moto import mock_swf_deprecated
from moto.core.utils import unix_time


# Utils
@mock_swf_deprecated
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
@mock_swf_deprecated
def test_start_workflow_execution():
    conn = setup_swf_environment()

    wf = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    wf.should.contain("runId")

@mock_swf_deprecated
def test_signal_workflow_execution():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    wfe = conn.signal_workflow_execution(
        "test-domain", "my_signal", "uid-abcd1234", "my_input", run_id)

    wfe = conn.describe_workflow_execution(
        "test-domain", run_id, "uid-abcd1234")

    wfe["openCounts"]["openDecisionTasks"].should.equal(2)

@mock_swf_deprecated
def test_start_already_started_workflow_execution():
    conn = setup_swf_environment()
    conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0")

    conn.start_workflow_execution.when.called_with(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    ).should.throw(SWFResponseError)


@mock_swf_deprecated
def test_start_workflow_execution_on_deprecated_type():
    conn = setup_swf_environment()
    conn.deprecate_workflow_type("test-domain", "test-workflow", "v1.0")

    conn.start_workflow_execution.when.called_with(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    ).should.throw(SWFResponseError)


# DescribeWorkflowExecution endpoint
@mock_swf_deprecated
def test_describe_workflow_execution():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    wfe = conn.describe_workflow_execution(
        "test-domain", run_id, "uid-abcd1234")
    wfe["executionInfo"]["execution"][
        "workflowId"].should.equal("uid-abcd1234")
    wfe["executionInfo"]["executionStatus"].should.equal("OPEN")


@mock_swf_deprecated
def test_describe_non_existent_workflow_execution():
    conn = setup_swf_environment()

    conn.describe_workflow_execution.when.called_with(
        "test-domain", "wrong-run-id", "wrong-workflow-id"
    ).should.throw(SWFResponseError)


# GetWorkflowExecutionHistory endpoint
@mock_swf_deprecated
def test_get_workflow_execution_history():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    resp = conn.get_workflow_execution_history(
        "test-domain", run_id, "uid-abcd1234")
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])


@mock_swf_deprecated
def test_get_workflow_execution_history_with_reverse_order():
    conn = setup_swf_environment()
    hsh = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0")
    run_id = hsh["runId"]

    resp = conn.get_workflow_execution_history("test-domain", run_id, "uid-abcd1234",
                                               reverse_order=True)
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["DecisionTaskScheduled", "WorkflowExecutionStarted"])


@mock_swf_deprecated
def test_get_workflow_execution_history_on_non_existent_workflow_execution():
    conn = setup_swf_environment()

    conn.get_workflow_execution_history.when.called_with(
        "test-domain", "wrong-run-id", "wrong-workflow-id"
    ).should.throw(SWFResponseError)


# ListOpenWorkflowExecutions endpoint
@mock_swf_deprecated
def test_list_open_workflow_executions():
    conn = setup_swf_environment()
    # One open workflow execution
    conn.start_workflow_execution(
        'test-domain', 'uid-abcd1234', 'test-workflow', 'v1.0'
    )
    # One closed workflow execution to make sure it isn't displayed
    run_id = conn.start_workflow_execution(
        'test-domain', 'uid-abcd12345', 'test-workflow', 'v1.0'
    )['runId']
    conn.terminate_workflow_execution('test-domain', 'uid-abcd12345',
                                      details='some details',
                                      reason='a more complete reason',
                                      run_id=run_id)

    yesterday = datetime.utcnow() - timedelta(days=1)
    oldest_date = unix_time(yesterday)
    response = conn.list_open_workflow_executions('test-domain',
                                                  oldest_date,
                                                  workflow_id='test-workflow')
    execution_infos = response['executionInfos']
    len(execution_infos).should.equal(1)
    open_workflow = execution_infos[0]
    open_workflow['workflowType'].should.equal({'version': 'v1.0',
                                                'name': 'test-workflow'})
    open_workflow.should.contain('startTimestamp')
    open_workflow['execution']['workflowId'].should.equal('uid-abcd1234')
    open_workflow['execution'].should.contain('runId')
    open_workflow['cancelRequested'].should.be(False)
    open_workflow['executionStatus'].should.equal('OPEN')


# ListClosedWorkflowExecutions endpoint
@mock_swf_deprecated
def test_list_closed_workflow_executions():
    conn = setup_swf_environment()
    # Leave one workflow execution open to make sure it isn't displayed
    conn.start_workflow_execution(
        'test-domain', 'uid-abcd1234', 'test-workflow', 'v1.0'
    )
    # One closed workflow execution
    run_id = conn.start_workflow_execution(
        'test-domain', 'uid-abcd12345', 'test-workflow', 'v1.0'
    )['runId']
    conn.terminate_workflow_execution('test-domain', 'uid-abcd12345',
                                      details='some details',
                                      reason='a more complete reason',
                                      run_id=run_id)

    yesterday = datetime.utcnow() - timedelta(days=1)
    oldest_date = unix_time(yesterday)
    response = conn.list_closed_workflow_executions(
        'test-domain',
        start_oldest_date=oldest_date,
        workflow_id='test-workflow')
    execution_infos = response['executionInfos']
    len(execution_infos).should.equal(1)
    open_workflow = execution_infos[0]
    open_workflow['workflowType'].should.equal({'version': 'v1.0',
                                                'name': 'test-workflow'})
    open_workflow.should.contain('startTimestamp')
    open_workflow['execution']['workflowId'].should.equal('uid-abcd12345')
    open_workflow['execution'].should.contain('runId')
    open_workflow['cancelRequested'].should.be(False)
    open_workflow['executionStatus'].should.equal('CLOSED')


# TerminateWorkflowExecution endpoint
@mock_swf_deprecated
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

    resp = conn.get_workflow_execution_history(
        "test-domain", run_id, "uid-abcd1234")
    evt = resp["events"][-1]
    evt["eventType"].should.equal("WorkflowExecutionTerminated")
    attrs = evt["workflowExecutionTerminatedEventAttributes"]
    attrs["details"].should.equal("some details")
    attrs["reason"].should.equal("a more complete reason")
    attrs["cause"].should.equal("OPERATOR_INITIATED")


@mock_swf_deprecated
def test_terminate_workflow_execution_with_wrong_workflow_or_run_id():
    conn = setup_swf_environment()
    run_id = conn.start_workflow_execution(
        "test-domain", "uid-abcd1234", "test-workflow", "v1.0"
    )["runId"]

    # terminate workflow execution
    conn.terminate_workflow_execution("test-domain", "uid-abcd1234")

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
