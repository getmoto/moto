import boto3

from moto import mock_iam, mock_s3, mock_ecs, mock_logs, settings, mock_lambda_simple
from uuid import uuid4
from unittest import mock, SkipTest
import pytest
from botocore.exceptions import ClientError, ParamValidationError
import json
from ..test_awslambda.utilities import (
    get_test_zip_file1,
)

LAMBDA_REGION = 'us-west-2'
PYTHON_VERSION='3.11'
FUNCTION_NAME = "test-function-123"


@mock_iam
def get_role_name():
    with mock_iam():
        iam = boto3.client("iam", region_name=LAMBDA_REGION)
        while True:
            try:
                return iam.get_role(RoleName="my-role")["Role"]["Arn"]
            except ClientError:
                try:
                    return iam.create_role(
                        RoleName="my-role",
                        AssumeRolePolicyDocument="some policy",
                        Path="/my-path/",
                    )["Role"]["Arn"]
                except ClientError:
                    pass
@mock_s3
@mock_logs
@mock_iam
@mock_lambda_simple
def test_run_function():
    client = boto3.client("lambda", LAMBDA_REGION)
    zip_content = get_test_zip_file1()
    function_name = FUNCTION_NAME
    role = get_role_name()
    client.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=role,
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    # client = boto3.client('lambda')
    response = client.invoke(
        FunctionName=FUNCTION_NAME, Payload=json.dumps({}), LogType="Tail",
    )

# @mock_s3
# @mock_logs
# @mock_iam
# @mock_lambda
# @pytest.fixture
# def dummy_function():
#     conn = boto3.client("lambda", LAMBDA_REGION)
#     zip_content = get_test_zip_file1()
#     function_name = FUNCTION_NAME
#     role = get_role_name()
#     conn.create_function(
#         FunctionName=function_name,
#         Runtime=PYTHON_VERSION,
#         Role=role,
#         Handler="lambda_function.lambda_handler",
#         Code={"ZipFile": zip_content},
#         Description="test lambda function",
#         Timeout=3,
#         MemorySize=128,
#         Publish=True,
#     )