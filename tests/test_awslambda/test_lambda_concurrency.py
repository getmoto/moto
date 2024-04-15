from uuid import uuid4

import boto3
import pytest

from moto import mock_aws

from .utilities import get_role_name, get_test_zip_file1

PYTHON_VERSION = "python3.11"
_lambda_region = "us-west-2"


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_aws
def test_put_function_concurrency(key):
    expected_concurrency = 15
    function_name = str(uuid4())[0:6]

    conn = boto3.client("lambda", _lambda_region)
    f = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = f[key]
    result = conn.put_function_concurrency(
        FunctionName=name_or_arn, ReservedConcurrentExecutions=expected_concurrency
    )

    assert result["ReservedConcurrentExecutions"] == expected_concurrency


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_aws
def test_delete_function_concurrency(key):
    function_name = str(uuid4())[0:6]

    conn = boto3.client("lambda", _lambda_region)
    f = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = f[key]
    conn.put_function_concurrency(
        FunctionName=name_or_arn, ReservedConcurrentExecutions=15
    )

    conn.delete_function_concurrency(FunctionName=name_or_arn)
    result = conn.get_function(FunctionName=function_name)

    assert "Concurrency" not in result


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_aws
def test_get_function_concurrency(key):
    expected_concurrency = 15
    function_name = str(uuid4())[0:6]

    conn = boto3.client("lambda", _lambda_region)
    f = conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = f[key]
    conn.put_function_concurrency(
        FunctionName=name_or_arn, ReservedConcurrentExecutions=expected_concurrency
    )

    result = conn.get_function_concurrency(FunctionName=name_or_arn)

    assert result["ReservedConcurrentExecutions"] == expected_concurrency
