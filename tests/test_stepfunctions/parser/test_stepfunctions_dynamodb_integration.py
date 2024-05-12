import json
import os
from functools import wraps
from uuid import uuid4

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws

from . import base_url, verify_execution_result


def aws_verified(func):
    """
    Function that is verified to work against AWS.
    Can be run against AWS at any time by setting:
      MOTO_TEST_ALLOW_AWS_REQUEST=true

    If this environment variable is not set, the function runs in a `mock_aws` context.

    This decorator will:
      - Create an IAM-role that can be used by AWSLambda functions table
      - Run the test
      - Delete the role
    """

    @wraps(func)
    def pagination_wrapper():
        table_name = "table_" + str(uuid4())[0:6]

        allow_aws_request = (
            os.environ.get("MOTO_TEST_ALLOW_AWS_REQUEST", "false").lower() == "true"
        )

        if allow_aws_request:
            return create_table_and_test(table_name, sleep_time=10)
        else:
            with mock_aws():
                requests.post(
                    f"http://{base_url}/moto-api/config",
                    json={"stepfunctions": {"execute_state_machine": True}},
                )
                resp = create_table_and_test(table_name, sleep_time=0)
                requests.post(
                    f"http://{base_url}/moto-api/config",
                    json={"stepfunctions": {"execute_state_machine": False}},
                )
                return resp

    def create_table_and_test(table_name, sleep_time):
        client = boto3.client("dynamodb", region_name="us-east-1")

        client.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 5},
            Tags=[{"Key": "environment", "Value": "moto_tests"}],
        )
        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        try:
            resp = func(table_name, sleep_time)
        finally:
            ### CLEANUP ###
            client.delete_table(TableName=table_name)

        return resp

    return pagination_wrapper


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_calling_dynamodb_put(table_name=None, sleep_time=0):
    dynamodb = boto3.client("dynamodb", "us-east-1")
    exec_input = {
        "TableName": table_name,
        "Item": {"data": {"S": "HelloWorld"}, "id": {"S": "id1"}},
    }

    expected_status = "SUCCEEDED"
    tmpl_name = "services/dynamodb_put_item"

    def _verify_result(client, execution, execution_arn):
        assert "stopDate" in execution
        assert json.loads(execution["input"]) == exec_input

        items = dynamodb.scan(TableName=table_name)["Items"]
        assert items == [exec_input["Item"]]

    verify_execution_result(
        _verify_result,
        expected_status,
        tmpl_name,
        exec_input=json.dumps(exec_input),
        sleep_time=sleep_time,
    )


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_calling_dynamodb_put_wait_for_invalid_task_token(
    table_name=None, sleep_time=0
):
    dynamodb = boto3.client("dynamodb", "us-east-1")
    exec_input = {
        "TableName": table_name,
        "Item": {"data": {"S": "HelloWorld"}, "id": {"S": "id1"}},
    }

    tmpl_name = "services/dynamodb_invalid_task_token"

    def _verify_result(client, execution, execution_arn):
        if execution["status"] == "RUNNING":
            items = dynamodb.scan(TableName=table_name)["Items"]
            if len(items) > 0:
                assert len(items) == 1
                assert items[0]["id"] == {"S": "1"}
                assert items[0]["StepFunctionTaskToken"] == {"S": "$$.Task.Token"}
                # Because the TaskToken is not returned, we can't signal to SFN to finish the execution
                # So let's just stop the execution manually
                client.stop_execution(
                    executionArn=execution_arn,
                    error="Bad Example - no TaskToken available to continue this execution",
                )
                return True

        return False

    verify_execution_result(
        _verify_result,
        expected_status=None,
        tmpl_name=tmpl_name,
        exec_input=json.dumps(exec_input),
        sleep_time=sleep_time,
    )


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_calling_dynamodb_put_wait_for_task_token(
    table_name=None, sleep_time=0
):
    dynamodb = boto3.client("dynamodb", "us-east-1")
    exec_input = {"TableName": table_name, "Item": {"id": {"S": "id1"}}}
    output = {"a": "b"}

    tmpl_name = "services/dynamodb_task_token"

    def _verify_result(client, execution, execution_arn):
        if execution["status"] == "RUNNING":
            items = dynamodb.scan(TableName=table_name)["Items"]
            if len(items) > 0:
                assert len(items) == 1
                assert items[0]["id"] == {"S": "1"}
                # Some random token
                assert len(items[0]["StepFunctionTaskToken"]["S"]) > 25
                token = items[0]["StepFunctionTaskToken"]["S"]
                client.send_task_success(taskToken=token, output=json.dumps(output))

        if execution["status"] == "SUCCEEDED":
            assert json.loads(execution["output"]) == output
            return True

        return False

    verify_execution_result(
        _verify_result,
        expected_status=None,
        tmpl_name=tmpl_name,
        exec_input=json.dumps(exec_input),
        sleep_time=sleep_time,
    )


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_calling_dynamodb_put_fail_task_token(
    table_name=None, sleep_time=0
):
    dynamodb = boto3.client("dynamodb", "us-east-1")
    exec_input = {"TableName": table_name, "Item": {"id": {"S": "id1"}}}

    tmpl_name = "services/dynamodb_task_token"

    def _verify_result(client, execution, execution_arn):
        if execution["status"] == "RUNNING":
            items = dynamodb.scan(TableName=table_name)["Items"]
            if len(items) > 0:
                assert len(items) == 1
                assert items[0]["id"] == {"S": "1"}
                # Some random token
                assert len(items[0]["StepFunctionTaskToken"]["S"]) > 25
                token = items[0]["StepFunctionTaskToken"]["S"]
                client.send_task_failure(taskToken=token, error="test error")

        if execution["status"] == "FAILED":
            assert execution["error"] == "test error"
            return True

        return False

    verify_execution_result(
        _verify_result,
        expected_status=None,
        tmpl_name=tmpl_name,
        exec_input=json.dumps(exec_input),
        sleep_time=sleep_time,
    )


@aws_verified
@pytest.mark.aws_verified
def test_state_machine_calling_dynamodb_put_and_delete(table_name=None, sleep_time=0):
    dynamodb = boto3.client("dynamodb", "us-east-1")
    exec_input = {
        "TableName": table_name,
        "Item1": {"data": {"S": "HelloWorld"}, "id": {"S": "id1"}},
        "Item2": {"data": {"S": "HelloWorld"}, "id": {"S": "id2"}},
        "Key": {"id": {"S": "id1"}},
    }

    expected_status = "SUCCEEDED"
    tmpl_name = "services/dynamodb_put_delete_item"

    def _verify_result(client, execution, execution_arn):
        assert "stopDate" in execution
        assert json.loads(execution["input"]) == exec_input

        items = dynamodb.scan(TableName=table_name)["Items"]
        assert items == [exec_input["Item2"]]

    verify_execution_result(
        _verify_result,
        expected_status,
        tmpl_name,
        exec_input=json.dumps(exec_input),
        sleep_time=sleep_time,
    )


@aws_verified
@pytest.mark.aws_verified
def test_send_task_failure_invalid_token(table_name=None, sleep_time=0):
    dynamodb = boto3.client("dynamodb", "us-east-1")
    exec_input = {"TableName": table_name, "Item": {"id": {"S": "id1"}}}

    tmpl_name = "services/dynamodb_task_token"

    def _verify_result(client, execution, execution_arn):
        if execution["status"] == "RUNNING":
            items = dynamodb.scan(TableName=table_name)["Items"]
            if len(items) > 0:
                # Execute
                with pytest.raises(ClientError) as exc:
                    client.send_task_failure(taskToken="bad_token", error="test error")

                # Verify
                assert (
                    exc.value.response["Error"]["Code"] == "UnrecognizedClientException"
                )
                assert (
                    exc.value.response["Error"]["Message"]
                    == "The security token included "
                    "in the request is invalid."
                )

                # Execute
                with pytest.raises(ClientError) as exc:
                    client.send_task_success(
                        taskToken="bad_token", output="test output"
                    )

                # Verify
                assert (
                    exc.value.response["Error"]["Code"] == "UnrecognizedClientException"
                )
                assert (
                    exc.value.response["Error"]["Message"]
                    == "The security token included "
                    "in the request is invalid."
                )

    verify_execution_result(
        _verify_result,
        expected_status=None,
        tmpl_name=tmpl_name,
        exec_input=json.dumps(exec_input),
        sleep_time=sleep_time,
    )
