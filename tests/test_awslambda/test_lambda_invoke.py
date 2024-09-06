import base64
import json
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import set_initial_no_auth_action_count

from ..markers import requires_docker
from .test_lambda import LooseVersion, boto3_version
from .utilities import (
    get_lambda_using_environment_port,
    get_lambda_using_network_mode,
    get_proxy_zip_file,
    get_role_name,
    get_test_zip_file1,
    get_test_zip_file2,
    get_test_zip_file_error,
    get_test_zip_largeresponse,
    get_zip_with_multiple_files,
)

PYTHON_VERSION = "python3.11"
_lambda_region = "us-west-2"


@pytest.mark.network
@requires_docker
class TestLambdaInvocations_Error:
    mock = mock_aws()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        cls.client = boto3.client("lambda", _lambda_region)
        cls.function_name = str(uuid4())[0:6]
        cls.client.create_function(
            FunctionName=cls.function_name,
            Runtime=PYTHON_VERSION,
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": get_test_zip_file_error()},
        )

    @classmethod
    def teardown_class(cls):
        try:
            cls.mock.stop()
        except RuntimeError:
            pass

    @pytest.mark.parametrize("invocation_type", [None, "RequestResponse"])
    def test_invoke_function_that_throws_error(self, invocation_type):
        kw = {"LogType": "Tail"}
        if invocation_type:
            kw["InvocationType"] = invocation_type

        failure_response = TestLambdaInvocations_Error.client.invoke(
            FunctionName=self.function_name, Payload=json.dumps({}), **kw
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
@requires_docker
class TestLambdaInvocations:
    mock = mock_aws()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        cls.client = boto3.client("lambda", _lambda_region)
        cls.function_name = str(uuid4())[0:6]
        cls.fxn = cls.client.create_function(
            FunctionName=cls.function_name,
            Runtime=PYTHON_VERSION,
            Role=get_role_name(),
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": get_test_zip_file1()},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )

    @classmethod
    def teardown_class(cls):
        try:
            cls.mock.stop()
        except RuntimeError:
            pass

    @pytest.mark.parametrize("invocation_type", [None, "RequestResponse"])
    @pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
    def test_invoke_requestresponse_function(self, invocation_type, key):
        name_or_arn = self.fxn[key]

        # Only add invocation-type keyword-argument when provided, otherwise the request
        # fails to be validated
        kw = {}
        if invocation_type:
            kw["InvocationType"] = invocation_type

        in_data = {"msg": "So long and thanks for all the fish"}
        success_result = self.client.invoke(
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
        success_result = self.client.invoke(
            FunctionName=name_or_arn, Payload=json.dumps(in_data), **kw
        )

        assert success_result["StatusCode"] == 200
        assert (
            success_result["ResponseMetadata"]["HTTPHeaders"]["content-type"]
            == "application/json"
        )
        assert "LogResult" not in success_result

    def test_invoke_event_function(self):
        with pytest.raises(ClientError):
            self.client.invoke(
                FunctionName="notAFunction", InvocationType="Event", Payload="{}"
            )

        in_data = {"msg": "So long and thanks for all the fish"}
        success_result = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="Event",
            Payload=json.dumps(in_data),
        )
        assert success_result["StatusCode"] == 202
        assert json.loads(success_result["Payload"].read().decode("utf-8")) == in_data

    def test_invoke_dryrun_function(self):
        in_data = {"msg": "So long and thanks for all the fish"}
        success_result = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType="DryRun",
            Payload=json.dumps(in_data),
        )
        assert success_result["StatusCode"] == 204

    @pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
    def test_invoke_async_function(self, key):
        name_or_arn = self.fxn[key]

        success_result = self.client.invoke_async(
            FunctionName=name_or_arn, InvokeArgs=json.dumps({"test": "event"})
        )

        assert success_result["Status"] == 202


@pytest.mark.network
@mock_aws
def test_invoke_lambda_using_environment_port():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest("Can only test environment variables in server mode")
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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
@mock_aws
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
        Runtime=PYTHON_VERSION,
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
@mock_aws
@requires_docker
def test_invoke_function_with_multiple_files_in_zip():
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
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


if settings.TEST_SERVER_MODE:

    @mock_aws
    def test_invoke_function_get_ec2_volume():
        conn = boto3.resource("ec2", _lambda_region)
        vol = conn.create_volume(Size=99, AvailabilityZone=_lambda_region)
        vol = conn.Volume(vol.id)

        conn = boto3.client("lambda", _lambda_region)
        function_name = str(uuid4())[0:6]
        conn.create_function(
            FunctionName=function_name,
            Runtime=PYTHON_VERSION,
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
@mock_aws
@requires_docker
@pytest.mark.xfail(message="Fails intermittently - functionality exists though")
def test_invoke_function_large_response():
    # AWS Lambda should only return bodies smaller than 6 MB
    conn = boto3.client("lambda", _lambda_region)
    fxn = conn.create_function(
        FunctionName=str(uuid4())[0:6],
        Runtime=PYTHON_VERSION,
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


@mock_aws
def test_invoke_lambda_with_proxy():
    if not settings.is_test_proxy_mode():
        raise SkipTest("We only want to test this in ProxyMode")

    conn = boto3.resource("ec2", _lambda_region)
    vol = conn.create_volume(Size=99, AvailabilityZone=_lambda_region)
    vol = conn.Volume(vol.id)

    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_proxy_zip_file()},
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
    payload = result["Payload"].read().decode("utf-8")

    expected_payload = {"id": vol.id, "state": vol.state, "size": vol.size}
    assert json.loads(payload) == expected_payload


@pytest.mark.network
@mock_aws
@requires_docker
def test_invoke_lambda_with_entrypoint():
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("ImageConfig parameter not available in older versions")
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
        ImageConfig={
            "EntryPoint": [
                "/var/rapid/init",
                "--bootstrap",
                "/var/runtime/bootstrap",
                "--enable-msg-logs",
            ],
        },
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    in_data = {"hello": "world"}
    result = conn.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(in_data),
    )
    assert result["StatusCode"] == 200
    payload = result["Payload"].read().decode("utf-8")

    assert json.loads(payload) == in_data


@set_initial_no_auth_action_count(4)
@mock_aws
def test_lambda_request_unauthorized_user():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Auth decorator does not work in server mode")
    iam = boto3.client("iam", region_name="us-west-2")
    user_name = "test-user"
    iam.create_user(UserName=user_name)
    policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Deny",
            "Action": ["s3:*", "secretsmanager:*", "lambda:*"],
            "Resource": "*",
        },
    }
    policy_arn = iam.create_policy(
        PolicyName="policy2", PolicyDocument=json.dumps(policy_document)
    )["Policy"]["Arn"]
    iam.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)
    access_key = iam.create_access_key(UserName=user_name)["AccessKey"]

    _lambda = boto3.session.Session(
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
        region_name="us-west-2",
    ).client(service_name="lambda")

    with pytest.raises(ClientError) as exc:
        _lambda.invoke(FunctionName="n/a", Payload="{}")
    assert "not authorized to perform: lambda:Invoke" in str(exc.value)
