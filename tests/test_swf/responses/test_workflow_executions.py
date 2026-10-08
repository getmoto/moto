from datetime import timedelta

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core.utils import unix_time, utcnow


def setup_swf_environment():
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
@mock_aws
def test_start_workflow_execution():
    client = setup_swf_environment()

    wf = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    assert "runId" in wf


@mock_aws
def test_signal_workflow_execution():
    client = setup_swf_environment()
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

    assert wfe["openCounts"]["openDecisionTasks"] == 2


@mock_aws
def test_signal_workflow_execution_without_runId():
    conn = setup_swf_environment()
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
    assert "WorkflowExecutionSignaled" in types


@mock_aws
def test_start_already_started_workflow_execution():
    client = setup_swf_environment()
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
    assert ex.value.response["Error"]["Code"] == "WorkflowExecutionAlreadyStartedFault"
    assert ex.value.response["Error"]["Message"] == "Already Started"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_start_workflow_execution_on_deprecated_type():
    client = setup_swf_environment()
    client.deprecate_workflow_type(
        domain="test-domain", workflowType={"name": "test-workflow", "version": "v1.0"}
    )

    with pytest.raises(ClientError) as ex:
        client.start_workflow_execution(
            domain="test-domain",
            workflowId="uid-abcd1234",
            workflowType={"name": "test-workflow", "version": "v1.0"},
        )
    assert ex.value.response["Error"]["Code"] == "TypeDeprecatedFault"
    assert ex.value.response["Error"]["Message"] == (
        "WorkflowType=[name=test-workflow, version=v1.0]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# DescribeWorkflowExecution endpoint
@mock_aws
def test_describe_workflow_execution():
    client = setup_swf_environment()
    hsh = client.start_workflow_execution(
        domain="test-domain",
        workflowId="uid-abcd1234",
        workflowType={"name": "test-workflow", "version": "v1.0"},
    )
    run_id = hsh["runId"]

    wfe = client.describe_workflow_execution(
        domain="test-domain", execution={"runId": run_id, "workflowId": "uid-abcd1234"}
    )
    assert wfe["executionInfo"]["execution"]["workflowId"] == "uid-abcd1234"
    assert wfe["executionInfo"]["executionStatus"] == "OPEN"


@mock_aws
def test_describe_non_existent_workflow_execution():
    client = setup_swf_environment()

    with pytest.raises(ClientError) as ex:
        client.describe_workflow_execution(
            domain="test-domain",
            execution={"runId": "wrong-run-id", "workflowId": "uid-abcd1234"},
        )
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId=wrong-run-id]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# GetWorkflowExecutionHistory endpoint
@mock_aws
def test_get_workflow_execution_history():
    client = setup_swf_environment()
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
    assert types == ["WorkflowExecutionStarted", "DecisionTaskScheduled"]


@mock_aws
def test_get_workflow_execution_history_with_reverse_order():
    client = setup_swf_environment()
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
    assert types == ["DecisionTaskScheduled", "WorkflowExecutionStarted"]


@mock_aws
def test_get_workflow_execution_history_on_non_existent_workflow_execution():
    client = setup_swf_environment()

    with pytest.raises(ClientError) as ex:
        client.get_workflow_execution_history(
            domain="test-domain",
            execution={"runId": "wrong-run-id", "workflowId": "wrong-workflow-id"},
        )
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown execution: WorkflowExecution=[workflowId=wrong-workflow-id, runId=wrong-run-id]"
    )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
@pytest.mark.parametrize(
    "operation", ["describe_workflow_execution", "get_workflow_execution_history"]
)
@pytest.mark.parametrize(
    "parameter,bad_value",
    [("domain", 123), ("execution.runId", 123), ("execution.workflowId", [])],
)
@pytest.mark.parametrize("case", ["missing", "null", "invalid-type"])
def test_workflow_execution_invalid_parameters(operation, parameter, bad_value, case):
    config = Config(parameter_validation=False)
    client = boto3.client("swf", region_name="us-west-1", config=config)
    parameters = {
        "domain": "test-domain",
        "execution": {"runId": "run-id", "workflowId": "workflow-id"},
    }
    parent, _, field = parameter.rpartition(".")
    target = parameters[parent] if parent else parameters
    if case == "missing":
        target.pop(field)
    else:
        target[field] = None if case == "null" else bad_value

    with pytest.raises(ClientError) as ex:
        getattr(client, operation)(**parameters)

    error = ex.value.response["Error"]
    if case == "invalid-type":
        assert error["Code"] == "SerializationException"
    else:
        assert error["Code"] == "ValidationException"
        assert error["Message"] == (
            f"1 validation error detected: Value null at '{parameter}' "
            "failed to satisfy constraint: Member must not be null"
        )
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
@pytest.mark.parametrize(
    "operation", ["describe_workflow_execution", "get_workflow_execution_history"]
)
@pytest.mark.parametrize(
    "parameters,message",
    [
        (
            {},
            "2 validation errors detected: Value null at 'execution' failed to satisfy constraint: Member must not be null; Value null at 'domain' failed to satisfy constraint: Member must not be null",
        ),
        (
            {"domain": "test-domain"},
            "1 validation error detected: Value null at 'execution' failed to satisfy constraint: Member must not be null",
        ),
        (
            {"domain": "test-domain", "execution": {}},
            "2 validation errors detected: Value null at 'execution.runId' failed to satisfy constraint: Member must not be null; Value null at 'execution.workflowId' failed to satisfy constraint: Member must not be null",
        ),
    ],
)
def test_workflow_execution_missing_execution(operation, parameters, message):
    config = Config(parameter_validation=False)
    client = boto3.client("swf", region_name="us-west-1", config=config)

    with pytest.raises(ClientError) as ex:
        getattr(client, operation)(**parameters)

    assert ex.value.response["Error"]["Code"] == "ValidationException"
    assert ex.value.response["Error"]["Message"] == message
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


# ListOpenWorkflowExecutions endpoint
@mock_aws
def test_list_open_workflow_executions():
    client = setup_swf_environment()
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

    yesterday = utcnow() - timedelta(days=1)
    oldest_date = unix_time(yesterday)
    response = client.list_open_workflow_executions(
        domain="test-domain",
        startTimeFilter={"oldestDate": oldest_date},
        executionFilter={"workflowId": "test-workflow"},
    )
    execution_infos = response["executionInfos"]
    assert len(execution_infos) == 1
    open_workflow = execution_infos[0]
    assert open_workflow["workflowType"] == {"version": "v1.0", "name": "test-workflow"}
    assert "startTimestamp" in open_workflow
    assert open_workflow["execution"]["workflowId"] == "uid-abcd1234"
    assert "runId" in open_workflow["execution"]
    assert open_workflow["cancelRequested"] is False
    assert open_workflow["executionStatus"] == "OPEN"


# ListClosedWorkflowExecutions endpoint
@mock_aws
def test_list_closed_workflow_executions():
    client = setup_swf_environment()
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

    yesterday = utcnow() - timedelta(days=1)
    oldest_date = unix_time(yesterday)
    response = client.list_closed_workflow_executions(
        domain="test-domain",
        startTimeFilter={"oldestDate": oldest_date},
        executionFilter={"workflowId": "test-workflow"},
    )
    execution_infos = response["executionInfos"]
    assert len(execution_infos) == 1
    open_workflow = execution_infos[0]
    assert open_workflow["workflowType"] == {"version": "v1.0", "name": "test-workflow"}
    assert "startTimestamp" in open_workflow
    assert open_workflow["execution"]["workflowId"] == "uid-abcd12345"
    assert "runId" in open_workflow["execution"]
    assert open_workflow["cancelRequested"] is False
    assert open_workflow["executionStatus"] == "CLOSED"


# TerminateWorkflowExecution endpoint
@mock_aws
def test_terminate_workflow_execution():
    client = setup_swf_environment()
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
    assert evt["eventType"] == "WorkflowExecutionTerminated"
    attrs = evt["workflowExecutionTerminatedEventAttributes"]
    assert attrs["details"] == "some details"
    assert attrs["reason"] == "a more complete reason"
    assert attrs["cause"] == "OPERATOR_INITIATED"


@mock_aws
def test_terminate_workflow_execution_with_wrong_workflow_or_run_id():
    client = setup_swf_environment()
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
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        f"Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId={run_id}]"
    )

    # already closed, without run_id
    with pytest.raises(ClientError) as ex:
        client.terminate_workflow_execution(
            domain="test-domain", workflowId="uid-abcd1234"
        )
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown execution, workflowId = uid-abcd1234"
    )

    # wrong workflow id
    with pytest.raises(ClientError) as ex:
        client.terminate_workflow_execution(
            domain="test-domain", workflowId="uid-non-existent"
        )
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown execution, workflowId = uid-non-existent"
    )

    # wrong run_id
    with pytest.raises(ClientError) as ex:
        client.terminate_workflow_execution(
            domain="test-domain", workflowId="uid-abcd1234", runId="foo"
        )
    assert ex.value.response["Error"]["Code"] == "UnknownResourceFault"
    assert ex.value.response["Error"]["Message"] == (
        "Unknown execution: WorkflowExecution=[workflowId=uid-abcd1234, runId=foo]"
    )
