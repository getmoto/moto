from datetime import datetime, timezone

from moto.stepfunctions.parser.asl.component.state.exec.state_task.service.resource import (
    ResourceARN,
    ServiceResource,
)
from moto.stepfunctions.parser.asl.component.state.exec.state_task.service.state_task_service_sfn import (
    StateTaskServiceSfn,
)

CHILD_ARN = "arn:aws:states:us-east-1:123456789012:stateMachine:child"
EXECUTION_ARN = "arn:aws:states:us-east-1:123456789012:execution:child:run1"


def _sfn_service(resource_arn: str) -> StateTaskServiceSfn:
    service = StateTaskServiceSfn()
    service.resource = ServiceResource(ResourceARN.from_arn(resource_arn))
    return service


def test_normalise_parameters_converts_pascal_case_to_boto_casing():
    # Regression test for https://github.com/getmoto/moto/issues/10076
    #
    # The `arn:aws:states:::states:startExecution(.sync|.sync:2)` service
    # integration's ASL Parameters use the (Pascal-cased) Step Functions API
    # member names (StateMachineArn, Input, Name, TraceHeader), but boto3's
    # `start_execution` expects its own (lowerCamel) member names
    # (stateMachineArn, input, name, traceHeader). Without normalisation,
    # botocore's serializer raises `KeyError: 'Input'`.
    service = _sfn_service("arn:aws:states:::states:startExecution.sync:2")
    parameters = {
        "StateMachineArn": CHILD_ARN,
        "Input": {"foo": "bar"},
        "Name": "child-exec",
        "TraceHeader": "trace-1",
    }

    service._normalise_parameters(parameters)

    assert parameters == {
        "stateMachineArn": CHILD_ARN,
        "input": '{"foo":"bar"}',
        "name": "child-exec",
        "traceHeader": "trace-1",
    }


def test_normalise_parameters_plain_start_execution():
    # The plain (non-.sync) `states:startExecution` integration goes through
    # the same normalisation.
    service = _sfn_service("arn:aws:states:::states:startExecution")
    parameters = {"StateMachineArn": CHILD_ARN, "Name": "child-exec"}

    service._normalise_parameters(parameters)

    assert parameters == {
        "stateMachineArn": CHILD_ARN,
        "name": "child-exec",
        # "Input" defaults to "{}" even when not supplied.
        "input": "{}",
    }


def test_normalise_response_converts_boto_casing_for_start_execution_output():
    # The immediate (non-.sync) task output of `states:startExecution` is the
    # boto3 StartExecution response, whose (lowerCamel) member names must be
    # converted back to the ASL/SFN (Pascal-cased) names.
    service = _sfn_service("arn:aws:states:::states:startExecution")
    response = {
        "executionArn": EXECUTION_ARN,
        "startDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
    }

    service._normalise_response(response)

    assert set(response.keys()) == {"ExecutionArn", "StartDate"}
    assert response["ExecutionArn"] == EXECUTION_ARN


def test_normalise_response_converts_boto_casing_for_describe_execution_output():
    # The `.sync`/`.sync:2` task output is built from a DescribeExecution
    # response, whose (lowerCamel) member names must likewise be converted
    # back to the ASL/SFN (Pascal-cased) names (this is the "response" half
    # of the same regression: `submission_output["ExecutionArn"]` and the
    # `.sync:2` resolvers only work if this normalisation has run).
    service = _sfn_service("arn:aws:states:::states:startExecution.sync:2")
    response = {
        "executionArn": EXECUTION_ARN,
        "stateMachineArn": CHILD_ARN,
        "name": "run1",
        "status": "SUCCEEDED",
        "startDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "stopDate": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "input": {"foo": "bar"},
        "output": {"child": "done"},
    }

    service._normalise_response(response, service_action_name="describe_execution")

    assert response["ExecutionArn"] == EXECUTION_ARN
    assert response["StateMachineArn"] == CHILD_ARN
    assert response["Name"] == "run1"
    assert response["Status"] == "SUCCEEDED"
    assert response["Input"] == {"foo": "bar"}
    assert response["Output"] == {"child": "done"}
    assert "executionArn" not in response
    assert "stateMachineArn" not in response
