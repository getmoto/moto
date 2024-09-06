import json
from time import sleep
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest

from moto import settings

from . import (
    allow_aws_request,
    aws_verified,
    sfn_allow_dynamodb,
    sfn_role_policy,
    verify_execution_result,
)


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_with_simple_failure_state():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Don't need to test this in ServerMode")

    def _verify_result(client, execution, execution_arn):
        assert "stopDate" in execution
        assert execution["error"] == "DefaultStateError"
        assert execution["cause"] == "No Matches!"
        assert execution["input"] == "{}"

        history = client.get_execution_history(executionArn=execution_arn)
        assert len(history["events"]) == 3
        assert [e["type"] for e in history["events"]] == [
            "ExecutionStarted",
            "FailStateEntered",
            "ExecutionFailed",
        ]

        state_machine_arn = execution["stateMachineArn"]
        executions = client.list_executions(stateMachineArn=state_machine_arn)[
            "executions"
        ]
        assert len(executions) == 1
        assert executions[0]["executionArn"] == execution_arn
        assert executions[0]["stateMachineArn"] == state_machine_arn
        assert executions[0]["status"] == "FAILED"

    verify_execution_result(_verify_result, "FAILED", "failure")


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_with_input():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Don't need to test this in ServerMode")

    _input = {"my": "data"}

    def _verify_result(client, execution, execution_arn):
        assert execution["input"] == json.dumps(_input)

    verify_execution_result(
        _verify_result,
        "FAILED",
        "failure",
        exec_input=json.dumps(_input),
    )


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_with_json_regex():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Don't need to test this in ServerMode")

    _input = {"Parameters": [{"Name": "/eggs/cooked/like", "Value": "poached"}]}
    _output = {
        "Parameters": [{"Name": "/eggs/cooked/like", "Value": "poached"}],
        "parameterTransforms": {"eggs": ["poached"]},
    }

    def _verify_result(client, execution, execution_arn):
        assert execution["input"] == json.dumps(_input)
        assert json.loads(execution["output"]) == _output
        return True

    verify_execution_result(
        _verify_result,
        "SUCCEEDED",
        "json_regex",
        exec_input=json.dumps(_input),
    )


@aws_verified
@pytest.mark.aws_verified
def test_version_is_only_available_when_published():
    from tests.test_stepfunctions.test_stepfunctions import simple_definition

    iam = boto3.client("iam", region_name="us-east-1")
    role_name = f"sfn_role_{str(uuid4())[0:6]}"
    sfn_role = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(sfn_role_policy),
        Path="/",
    )["Role"]["Arn"]
    iam.put_role_policy(
        PolicyDocument=json.dumps(sfn_allow_dynamodb),
        PolicyName="allowLambdaInvoke",
        RoleName=role_name,
    )
    sleep(10 if allow_aws_request() else 0)

    client = boto3.client("stepfunctions", region_name="us-east-1")

    try:
        name1 = f"sfn_name_{str(uuid4())[0:6]}"
        response = client.create_state_machine(
            name=name1, definition=simple_definition, roleArn=sfn_role
        )
        assert "stateMachineVersionArn" not in response
        arn1 = response["stateMachineArn"]

        resp = client.update_state_machine(
            stateMachineArn=arn1, publish=True, tracingConfiguration={"enabled": True}
        )
        assert resp["stateMachineVersionArn"] == f"{arn1}:1"

        resp = client.update_state_machine(
            stateMachineArn=arn1, tracingConfiguration={"enabled": False}
        )
        assert "stateMachineVersionArn" not in resp

        name2 = f"sfn_name_{str(uuid4())[0:6]}"
        response = client.create_state_machine(
            name=name2, definition=simple_definition, roleArn=sfn_role, publish=True
        )
        arn2 = response["stateMachineArn"]
        assert response["stateMachineVersionArn"] == f"{arn2}:1"

        resp = client.update_state_machine(
            stateMachineArn=arn2, publish=True, tracingConfiguration={"enabled": True}
        )
        assert resp["stateMachineVersionArn"] == f"{arn2}:2"
    finally:
        client.delete_state_machine(stateMachineArn=arn1)
        client.delete_state_machine(stateMachineArn=arn2)
        iam.delete_role_policy(RoleName=role_name, PolicyName="allowLambdaInvoke")
        iam.delete_role(RoleName=role_name)
