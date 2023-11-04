from unittest import SkipTest
import boto3

from moto import mock_iam, mock_lambda_simple, settings
from ..test_awslambda.utilities import get_test_zip_file1, get_role_name

LAMBDA_REGION = "us-west-2"
PYTHON_VERSION = "3.11"
FUNCTION_NAME = "test-function-123"

if settings.TEST_SERVER_MODE:
    raise SkipTest("No point in testing batch_simple in ServerMode")


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

    result = client.invoke(
        FunctionName=FUNCTION_NAME,
        LogType="Tail",
    )
    assert result["StatusCode"] == 200
    assert result["Payload"].read().decode("utf-8") == "Simple Lambda happy path OK"
