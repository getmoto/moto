import base64
import boto3
import io
import json
import pytest
import zipfile

from botocore.exceptions import ClientError
from moto import mock_lambda, mock_ec2, settings
from uuid import uuid4
from unittest import SkipTest
from .utilities import (
    get_role_name,
    get_test_zip_file_error,
    get_test_zip_file1,
    get_zip_with_multiple_files,
    get_test_zip_file2,
    get_lambda_using_environment_port,
    get_lambda_using_network_mode,
    get_test_zip_largeresponse,
)
from ..markers import requires_docker

_lambda_region = "us-west-2"


@pytest.mark.network
@mock_lambda
@requires_docker
def test_invoke_function_that_throws_error():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file_error()},
    )

    failure_response = conn.invoke(
        FunctionName=function_name, Payload=json.dumps({}), LogType="Tail"
    )

    assert failure_response["FunctionError"] == "Handled"

    payload = failure_response["Payload"].read().decode("utf-8")
    payload = json.loads(payload)
    assert payload["errorType"] == "Exception"
    assert payload["errorMessage"] == "I failed!"
    assert "stackTrace" in payload

    logs = base64.b64decode(failure_response["LogResult"]).decode("utf-8")
    assert "START RequestId:" in logs
    assert "I failed!" in logs
    assert "Traceback (most recent call last):" in logs
    assert "END RequestId:" in logs


@pytest.mark.network
@pytest.mark.parametrize("invocation_type", [None, "RequestResponse"])
@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@requires_docker
def test_invoke_requestresponse_function(invocation_type, key):
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = fxn[key]

    # Only add invocation-type keyword-argument when provided, otherwise the request
    # fails to be validated
    kw = {}
    if invocation_type:
        kw["InvocationType"] = invocation_type

    in_data = {"msg": "So long and thanks for all the fish"}
    success_result = conn.invoke(
        FunctionName=name_or_arn, Payload=json.dumps(in_data), LogType="Tail", **kw
    )

    if "FunctionError" in success_result:
        assert False, success_result["Payload"].read().decode("utf-8")

    assert success_result["StatusCode"] == 200
    assert (
        success_result["ResponseMetadata"]["HTTPHeaders"]["content-type"]
        == "application/json"
    )
    logs = base64.b64decode(success_result["LogResult"]).decode("utf-8")

    assert "START RequestId:" in logs
    assert "custom log event" in logs
    assert "END RequestId:" in logs

    payload = success_result["Payload"].read().decode("utf-8")
    assert json.loads(payload) == in_data

    # Logs should not be returned by default, only when the LogType-param is supplied
    success_result = conn.invoke(
        FunctionName=name_or_arn, Payload=json.dumps(in_data), **kw
    )

    assert success_result["StatusCode"] == 200
    assert (
        success_result["ResponseMetadata"]["HTTPHeaders"]["content-type"]
        == "application/json"
    )
    assert "LogResult" not in success_result


@pytest.mark.network
@mock_lambda
@requires_docker
def test_invoke_event_function():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.9",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    with pytest.raises(ClientError):
        conn.invoke(FunctionName="notAFunction", InvocationType="Event", Payload="{}")

    in_data = {"msg": "So long and thanks for all the fish"}
    success_result = conn.invoke(
        FunctionName=function_name, InvocationType="Event", Payload=json.dumps(in_data)
    )
    assert success_result["StatusCode"] == 202
    assert json.loads(success_result["Payload"].read().decode("utf-8")) == in_data


@pytest.mark.network
@mock_lambda
def test_invoke_lambda_using_environment_port():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest("Can only test environment variables in server mode")
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_lambda_using_environment_port()},
    )

    success_result = conn.invoke(
        FunctionName=function_name, InvocationType="Event", Payload="{}"
    )

    assert success_result["StatusCode"] == 202
    response = success_result["Payload"].read()
    response = json.loads(response.decode("utf-8"))

    functions = response["functions"]
    function_names = [f["FunctionName"] for f in functions]
    assert function_name in function_names

    # Host matches the full URL, so one of:
    # http://host.docker.internal:5000
    # http://172.0.2.1:5000
    # http://172.0.1.1:4555
    assert "http://" in response["host"]


@pytest.mark.network
@mock_lambda
def test_invoke_lambda_using_networkmode():
    """
    Special use case - verify that Lambda can send a request to 'http://localhost'
    This is only possible when the `network_mode` is set to host in the Docker args
    Test is only run in our CI (for now)
    """
    if not settings.moto_network_mode():
        raise SkipTest("Can only test this when NETWORK_MODE is specified")
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_lambda_using_network_mode()},
    )

    success_result = conn.invoke(
        FunctionName=function_name, InvocationType="Event", Payload="{}"
    )

    response = success_result["Payload"].read()
    functions = json.loads(response.decode("utf-8"))["response"]
    function_names = [f["FunctionName"] for f in functions]
    assert function_name in function_names


@pytest.mark.network
@mock_lambda
@requires_docker
def test_invoke_function_with_multiple_files_in_zip():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_zip_with_multiple_files()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    in_data = {"msg": "So long and thanks for: "}
    success_result = conn.invoke(
        FunctionName=function_name, InvocationType="Event", Payload=json.dumps(in_data)
    )
    assert json.loads(success_result["Payload"].read().decode("utf-8")) == {
        "msg": "So long and thanks for: stuff"
    }


@pytest.mark.network
@mock_lambda
@requires_docker
def test_invoke_dryrun_function():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    with pytest.raises(ClientError):
        conn.invoke(FunctionName="notAFunction", InvocationType="Event", Payload="{}")

    in_data = {"msg": "So long and thanks for all the fish"}
    success_result = conn.invoke(
        FunctionName=function_name, InvocationType="DryRun", Payload=json.dumps(in_data)
    )
    assert success_result["StatusCode"] == 204


if settings.TEST_SERVER_MODE:

    @mock_ec2
    @mock_lambda
    def test_invoke_function_get_ec2_volume():
        conn = boto3.resource("ec2", _lambda_region)
        vol = conn.create_volume(Size=99, AvailabilityZone=_lambda_region)
        vol = conn.Volume(vol.id)

        conn = boto3.client("lambda", _lambda_region)
        function_name = str(uuid4())[0:6]
        conn.create_function(
            FunctionName=function_name,
            Runtime="python3.7",
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": get_test_zip_file2()},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )

        in_data = {"volume_id": vol.id}
        result = conn.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(in_data),
        )
        assert result["StatusCode"] == 200
        actual_payload = json.loads(result["Payload"].read().decode("utf-8"))
        expected_payload = {"id": vol.id, "state": vol.state, "size": vol.size}
        assert actual_payload == expected_payload


@pytest.mark.network
@mock_lambda
@requires_docker
def test_invoke_lambda_error():
    lambda_fx = """
def lambda_handler(event, context):
    raise Exception('failsauce')
    """
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", lambda_fx)
    zip_file.close()
    zip_output.seek(0)

    client = boto3.client("lambda", region_name="us-east-1")
    client.create_function(
        FunctionName="test-lambda-fx",
        Runtime="python3.8",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Code={"ZipFile": zip_output.read()},
    )

    result = client.invoke(
        FunctionName="test-lambda-fx", InvocationType="RequestResponse", LogType="Tail"
    )

    assert "FunctionError" in result
    assert result["FunctionError"] == "Handled"


@pytest.mark.network
@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
@requires_docker
def test_invoke_async_function(key):
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    fxn = conn.create_function(
        FunctionName=function_name,
        Runtime="python3.8",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = fxn[key]

    success_result = conn.invoke_async(
        FunctionName=name_or_arn, InvokeArgs=json.dumps({"test": "event"})
    )

    assert success_result["Status"] == 202


@pytest.mark.network
@mock_lambda
@requires_docker
def test_invoke_function_large_response():
    # AWS Lambda should only return bodies smaller than 6 MB
    conn = boto3.client("lambda", _lambda_region)
    fxn = conn.create_function(
        FunctionName=str(uuid4())[0:6],
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_largeresponse()},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    resp = conn.invoke(FunctionName=fxn["FunctionArn"])
    assert resp["FunctionError"] == "Unhandled"
    payload = resp["Payload"].read().decode("utf-8")
    payload = json.loads(payload)
    assert payload == {
        "errorMessage": "Response payload size exceeded maximum allowed payload size (6291556 bytes).",
        "errorType": "Function.ResponseSizeTooLarge",
    }

    # Absolutely fine when invoking async
    resp = conn.invoke(FunctionName=fxn["FunctionArn"], InvocationType="Event")
    assert "FunctionError" not in resp
