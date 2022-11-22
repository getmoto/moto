import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_swf
from moto.core.utils import unix_time


def setup_swf_environment_boto3():
    client = boto3.client("swf", region_name="us-west-1")
    client.register_domain(
        name="test-domain",
        workflowExecutionRetentionPeriodInDays="60",
        description="A test domain",
    )
    client.register_workflow_type(
        domain="test-domain",
        name="test-workflow",
        version="v1.0",
        defaultTaskList={"name": "queue"},
        defaultChildPolicy="TERMINATE",
        defaultTaskStartToCloseTimeout="300",
        defaultExecutionStartToCloseTimeout="300",
    )
    client.register_activity_type(
        domain="test-domain", name="test-activity", version="v1.1"
    )
    return client


# StartWorkflowExecution endpoint
@mock_swf
def test_start_workflow_execution_boto3():
    client = setup_swf_environment_boto3()

    wf = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    wf.should.have.key("runId")


@mock_swf
def test_signal_workflow_execution_boto3():
    client = setup_swf_environment_boto3()
    hsh = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    run_id = hsh["runId"]

    wfe = client.signal_workflow_execution(
        domain="test-domain",
        signalName="my_signal",
        workflowId="uid-abcd1234",
        input="my_input",
        runId=run_id,
    )

    wfe = client.describe_workflow_execution(
        domain="test-domain", execution={"runId": run_id, "workflowId": "uid-abcd1234"}
    )

    wfe["openCounts"]["openDecisionTasks"].should.equal(2)


@mock_swf
def test_signal_workflow_execution_without_runId():
    conn = setup_swf_environment_boto3()
    hsh = conn.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    run_id = hsh["runId"]

    conn.signal_workflow_execution(
        domain="test-domain",
        signalName="my_signal",
        workflowId="uid-abcd1234",
        input="my_input",
    )

    resp = conn.get_workflow_execution_history(
        domain="test-domain", execution={"runId": run_id, "workflowId": "uid-abcd1234"}
    )

    types = [evt["eventType"] for evt in resp["events"]]
    types.should.contain("WorkflowExecutionSignaled")


@mock_swf
def test_start_already_started_workflow_execution_boto3():
    client = setup_swf_environment_boto3()
    client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )

    with pytest.raises(ClientError) as ex:
        client.start_workflow_execution(
            domain="test-domain",
            workflowId="uid-abcd1234",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )
    ex.value.response["Error"]["Code"].should.equal(
        "WorkflowExecutionAlreadyStartedFault"
    )
    ex.value.response["Error"]["Message"].should.equal("Already Started")
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


@mock_swf
def test_start_workflow_execution_on_deprecated_type_boto3():
    client = setup_swf_environment_boto3()
    client.deprecate_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )

    with pytest.raises(ClientError) as ex:
        client.start_workflow_execution(
            domain="test-domain",
            workflowId="uid-abcd1234",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )
    ex.value.response["Error"]["Code"].should.equal("TypeDeprecatedFault")
    ex.value.response["Error"]["Message"].should.equal(
        "WorkflowType=[name=test-workflow, version=v1.0]"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# DescribeWorkflowExecution endpoint
@mock_swf
def test_describe_workflow_execution_boto3():
    client = setup_swf_environment_boto3()
    hsh = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    run_id = hsh["runId"]

    wfe = client.describe_workflow_execution(
        domain="test-domain", execution={"runId": run_id, "workflowId": "uid-abcd1234"}
    )
    wfe["executionInfo"]["execution"]["workflowId"].should.equal("uid-abcd1234")
    wfe["executionInfo"]["executionStatus"].should.equal("OPEN")


@mock_swf
def test_describe_non_existent_workflow_execution_boto3():
    client = setup_swf_environment_boto3()

    with pytest.raises(ClientError) as ex:
        client.describe_workflow_execution(
            domain="test-domain",
            execution={"runId": "wrong-run-id", "workflowId": "uid-abcd1234"},
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId=wrong-run-id]"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# GetWorkflowExecutionHistory endpoint
@mock_swf
def test_get_workflow_execution_history_boto3():
    client = setup_swf_environment_boto3()
    hsh = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    run_id = hsh["runId"]

    resp = client.get_workflow_execution_history(
        domain="test-domain", execution={"runId": run_id, "workflowId": "uid-abcd1234"}
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["WorkflowExecutionStarted", "DecisionTaskScheduled"])


@mock_swf
def test_get_workflow_execution_history_with_reverse_order_boto3():
    client = setup_swf_environment_boto3()
    hsh = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    run_id = hsh["runId"]

    resp = client.get_workflow_execution_history(
        domain="test-domain",
        execution={"runId": run_id, "workflowId": "uid-abcd1234"},
        reverseOrder=True,
    )
    types = [evt["eventType"] for evt in resp["events"]]
    types.should.equal(["DecisionTaskScheduled", "WorkflowExecutionStarted"])


@mock_swf
def test_get_workflow_execution_history_on_non_existent_workflow_execution_boto3():
    client = setup_swf_environment_boto3()

    with pytest.raises(ClientError) as ex:
        client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": "wrong-run-id", "workflowId": "wrong-workflow-id"},
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown execution: WorkflowExecution=[workflowId=wrong-workflow-id, runId=wrong-run-id]"
    )
    ex.value.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)


# ListOpenWorkflowExecutions endpoint
@mock_swf
def test_list_open_workflow_executions_boto3():
    client = setup_swf_environment_boto3()
    # One open workflow execution
    client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    # One closed workflow execution to make sure it isn't displayed
    run_id = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd12345",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )["runId"]
    client.terminate_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd12345",
        details="some details",
        reason="a more complete reason",
        runId=run_id,
    )

    yesterday = datetime.utcnow() - timedelta(days=1)
    oldest_date = unix_time(yesterday)
    response = client.list_open_workflow_executions(
        domain="test-domain",
        startTimeFilter={"oldestDate": oldest_date},
        executionFilter={"workflowId": "test-workflow"},
    )
    execution_infos = response["executionInfos"]
    len(execution_infos).should.equal(1)
    open_workflow = execution_infos[0]
    open_workflow["workflowType"].should.equal(
        {"version": "v1.0", "name": "test-workflow"}
    )
    open_workflow.should.contain("startTimestamp")
    open_workflow["execution"]["workflowId"].should.equal("uid-abcd1234")
    open_workflow["execution"].should.contain("runId")
    open_workflow["cancelRequested"].should.be(False)
    open_workflow["executionStatus"].should.equal("OPEN")


# ListClosedWorkflowExecutions endpoint
@mock_swf
def test_list_closed_workflow_executions_boto3():
    client = setup_swf_environment_boto3()
    # Leave one workflow execution open to make sure it isn't displayed
    client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    # One closed workflow execution
    run_id = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd12345",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )["runId"]
    client.terminate_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd12345",
        details="some details",
        reason="a more complete reason",
        runId=run_id,
    )

    yesterday = datetime.utcnow() - timedelta(days=1)
    oldest_date = unix_time(yesterday)
    response = client.list_closed_workflow_executions(
        domain="test-domain",
        startTimeFilter={"oldestDate": oldest_date},
        executionFilter={"workflowId": "test-workflow"},
    )
    execution_infos = response["executionInfos"]
    len(execution_infos).should.equal(1)
    open_workflow = execution_infos[0]
    open_workflow["workflowType"].should.equal(
        {"version": "v1.0", "name": "test-workflow"}
    )
    open_workflow.should.contain("startTimestamp")
    open_workflow["execution"]["workflowId"].should.equal("uid-abcd12345")
    open_workflow["execution"].should.contain("runId")
    open_workflow["cancelRequested"].should.be(False)
    open_workflow["executionStatus"].should.equal("CLOSED")


# TerminateWorkflowExecution endpoint
@mock_swf
def test_terminate_workflow_execution_boto3():
    client = setup_swf_environment_boto3()
    run_id = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )["runId"]

    client.terminate_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        details="some details",
        reason="a more complete reason",
        runId=run_id,
    )

    resp = client.get_workflow_execution_history(
        domain="test-domain", execution={"runId": run_id, "workflowId": "uid-abcd1234"}
    )
    evt = resp["events"][-1]
    evt["eventType"].should.equal("WorkflowExecutionTerminated")
    attrs = evt["workflowExecutionTerminatedEventAttributes"]
    attrs["details"].should.equal("some details")
    attrs["reason"].should.equal("a more complete reason")
    attrs["cause"].should.equal("OPERATOR_INITIATED")


@mock_swf
def test_terminate_workflow_execution_with_wrong_workflow_or_run_id_boto3():
    client = setup_swf_environment_boto3()
    run_id = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )["runId"]

    # terminate workflow execution
    client.terminate_workflow_execution(domain="test-domain", workflowId="uid-abcd1234")

    # already closed, with run_id
    with pytest.raises(ClientError) as ex:
        client.terminate_workflow_execution(
            domain="test-domain", workflowId="uid-abcd1234", runId=run_id
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        f"Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId={run_id}]"
    )

    # already closed, without run_id
    with pytest.raises(ClientError) as ex:
        client.terminate_workflow_execution(
            domain="test-domain", workflowId="uid-abcd1234"
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown execution, workflowId = uid-abcd1234"
    )

    # wrong workflow id
    with pytest.raises(ClientError) as ex:
        client.terminate_workflow_execution(
            domain="test-domain", workflowId="uid-non-existent"
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown execution, workflowId = uid-non-existent"
    )

    # wrong run_id
    with pytest.raises(ClientError) as ex:
        client.terminate_workflow_execution(
            domain="test-domain", workflowId="uid-abcd1234", runId="foo"
        )
    ex.value.response["Error"]["Code"].should.equal("UnknownResourceFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId=foo]"
    )
