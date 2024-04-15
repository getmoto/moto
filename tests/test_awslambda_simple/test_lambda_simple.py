import json
from unittest import SkipTest

import boto3
import requests

from moto import mock_aws, settings

from ..test_awslambda.utilities import get_role_name, get_test_zip_file1

LAMBDA_REGION = "us-west-2"
PYTHON_VERSION = "3.11"
FUNCTION_NAME = "test-function-123"

if settings.TEST_SERVER_MODE:
    raise SkipTest("No point in testing batch_simple in ServerMode")


@mock_aws(config={"lambda": {"use_docker": False}})
def test_run_function():
    # Setup
    client = setup_lambda()

    # Execute
    result = client.invoke(
        FunctionName=FUNCTION_NAME,
        LogType="Tail",
    )

    # Verify
    assert result["StatusCode"] == 200
    assert result["Payload"].read().decode("utf-8") == "Simple Lambda happy path OK"


@mock_aws(config={"lambda": {"use_docker": False}})
def test_run_function_no_log():
    # Setup
    client = setup_lambda()
    payload = {"results": "results"}

    # Execute
    result = client.invoke(FunctionName=FUNCTION_NAME, Payload=json.dumps(payload))

    # Verify
    assert result["StatusCode"] == 200
    assert json.loads(result["Payload"].read().decode("utf-8")) == payload

    # Execute
    result = client.invoke(FunctionName=FUNCTION_NAME)

    # Verify
    assert result["StatusCode"] == 200
    assert result["Payload"].read().decode("utf-8") == "Simple Lambda happy path OK"


@mock_aws(config={"lambda": {"use_docker": False}})
def test_set_lambda_simple_query_results():
    # Setup
    base_url = (
        settings.test_server_mode_endpoint()
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )
    results = {"results": ["test", "test 2"], "region": LAMBDA_REGION}
    resp = requests.post(
        f"{base_url}/moto-api/static/lambda-simple/response",
        json=results,
    )
    assert resp.status_code == 201

    client = setup_lambda()

    # Execute & Verify
    resp = client.invoke(
        FunctionName=FUNCTION_NAME,
        LogType="Tail",
    )
    assert resp["Payload"].read().decode() == results["results"][0]

    resp = client.invoke(
        FunctionName=FUNCTION_NAME,
        LogType="Tail",
    )
    assert resp["Payload"].read().decode() == results["results"][1]

    resp = client.invoke(
        FunctionName=FUNCTION_NAME,
        LogType="Tail",
    )
    assert resp["Payload"].read().decode() == "Simple Lambda happy path OK"


def setup_lambda():
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
    return client
