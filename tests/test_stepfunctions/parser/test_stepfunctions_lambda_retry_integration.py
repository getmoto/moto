import json
from functools import wraps
from time import sleep
from uuid import uuid4

import boto3
import pytest
import requests

from moto import mock_aws
from tests.test_awslambda.utilities import get_test_zip_file_error

from ...markers import requires_docker
from . import base_url, sfn_role_policy
from .templates.retry import retry_template
from .templates.retry_jitter_none import retry_template_jitter_none


def create_failing_lambda_func(func):
    @wraps(func)
    def pagination_wrapper():
        role_name = "moto_test_role_" + str(uuid4())[0:6]

        with mock_aws():
            requests.post(
                f"http://{base_url}/moto-api/config",
                json={"stepfunctions": {"execute_state_machine": True}},
            )
            resp = create_role_and_test(role_name)
            requests.post(
                f"http://{base_url}/moto-api/config",
                json={"stepfunctions": {"execute_state_machine": False}},
            )
            return resp

    def create_role_and_test(role_name):
        policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "LambdaAssumeRole",
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        iam = boto3.client("iam", region_name="us-east-1")
        iam_role_arn = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(policy_doc),
            Path="/",
        )["Role"]["Arn"]

        fn_arn = create_function(iam_role_arn)

        return func(fn_arn)

    def create_function(role_arn: str):
        _lambda = boto3.client("lambda", "us-east-1")
        fn = _lambda.create_function(
            FunctionName=f"fn_{str(uuid4())[0:6]}",
            Runtime="python3.11",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": get_test_zip_file_error()},
        )
        return fn["FunctionArn"]

    return pagination_wrapper


@create_failing_lambda_func
@pytest.mark.network
@requires_docker
def test_retry_lambda(fn_arn=None):
    definition = retry_template.copy()
    definition["States"]["LambdaTask"]["Resource"] = fn_arn

    iam = boto3.client("iam", region_name="us-east-1")
    role_name = f"sfn_role_{str(uuid4())[0:6]}"
    sfn_role = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(sfn_role_policy),
        Path="/",
    )["Role"]["Arn"]

    client = boto3.client("stepfunctions", region_name="us-east-1")
    name = "sfn_" + str(uuid4())[0:6]
    exec_input = {"my": "input"}
    #
    response = client.create_state_machine(
        name=name, definition=json.dumps(definition), roleArn=sfn_role
    )
    state_machine_arn = response["stateMachineArn"]

    execution = client.start_execution(
        name="exec1", stateMachineArn=state_machine_arn, input=json.dumps(exec_input)
    )
    execution_arn = execution["executionArn"]

    for _ in range(25):
        execution = client.describe_execution(executionArn=execution_arn)
        if execution["status"] == "FAILED":
            history = client.get_execution_history(executionArn=execution_arn)
            assert len(history["events"]) == 12
            assert [e["type"] for e in history["events"]] == [
                "ExecutionStarted",
                "TaskStateEntered",
                "LambdaFunctionScheduled",
                "LambdaFunctionStarted",
                "LambdaFunctionFailed",
                "LambdaFunctionScheduled",
                "LambdaFunctionStarted",
                "LambdaFunctionFailed",
                "LambdaFunctionScheduled",
                "LambdaFunctionStarted",
                "LambdaFunctionFailed",
                "ExecutionFailed",
            ]

            break
        sleep(1)
    else:
        assert False, "Should have failed already"


@create_failing_lambda_func
@pytest.mark.network
@requires_docker
def test_retry_lambda_jitter_none(fn_arn=None):
    definition = retry_template_jitter_none.copy()
    definition["States"]["LambdaTask"]["Resource"] = fn_arn

    iam = boto3.client("iam", region_name="us-east-1")
    role_name = f"sfn_role_{str(uuid4())[0:6]}"
    sfn_role = iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(sfn_role_policy),
        Path="/",
    )["Role"]["Arn"]

    client = boto3.client("stepfunctions", region_name="us-east-1")
    name = "sfn_" + str(uuid4())[0:6]
    exec_input = {"my": "input"}
    #
    response = client.create_state_machine(
        name=name, definition=json.dumps(definition), roleArn=sfn_role
    )
    state_machine_arn = response["stateMachineArn"]

    execution = client.start_execution(
        name="exec1", stateMachineArn=state_machine_arn, input=json.dumps(exec_input)
    )
    execution_arn = execution["executionArn"]

    for _ in range(25):
        execution = client.describe_execution(executionArn=execution_arn)
        if execution["status"] == "FAILED":
            history = client.get_execution_history(executionArn=execution_arn)
            assert len(history["events"]) == 12
            assert [e["type"] for e in history["events"]] == [
                "ExecutionStarted",
                "TaskStateEntered",
                "LambdaFunctionScheduled",
                "LambdaFunctionStarted",
                "LambdaFunctionFailed",
                "LambdaFunctionScheduled",
                "LambdaFunctionStarted",
                "LambdaFunctionFailed",
                "LambdaFunctionScheduled",
                "LambdaFunctionStarted",
                "LambdaFunctionFailed",
                "ExecutionFailed",
            ]

            break
        sleep(1)
    else:
        assert False, "Should have failed already"
