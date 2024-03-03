import io
import json
import zipfile
from unittest import SkipTest
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError

from moto import mock_aws, settings

secret_steps = []


def mock_lambda_invoke(*args, **kwarg):
    secret_steps.append(json.loads(kwarg["body"])["Step"])
    return "n/a"


@mock_aws(config={"lambda": {"use_docker": False}})
@patch(
    "moto.awslambda_simple.models.LambdaSimpleBackend.invoke", new=mock_lambda_invoke
)
def test_simple_lambda_is_invoked():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test patched code in DecoratorMode")
    sm_client = boto3.client("secretsmanager", region_name="us-east-1")
    secret_arn = sm_client.create_secret(Name="some", SecretString="secret")["ARN"]

    lambda_res = create_mock_rotator_lambda()
    sm_client.rotate_secret(
        SecretId=secret_arn,
        RotationLambdaARN=lambda_res["FunctionArn"],
        RotationRules={"AutomaticallyAfterDays": 1, "Duration": "1h"},
        RotateImmediately=True,
    )
    assert secret_steps == ["createSecret", "setSecret", "testSecret", "finishSecret"]
    secret_steps.clear()


@mock_aws(config={"lambda": {"use_docker": False}})
@patch(
    "moto.awslambda_simple.models.LambdaSimpleBackend.invoke", new=mock_lambda_invoke
)
def test_simple_lambda_is_invoked__do_not_rotate_immediately():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only test patched code in DecoratorMode")
    sm_client = boto3.client("secretsmanager", region_name="us-east-1")
    secret_arn = sm_client.create_secret(Name="some", SecretString="secret")["ARN"]

    lambda_res = create_mock_rotator_lambda()
    sm_client.rotate_secret(
        SecretId=secret_arn,
        RotationLambdaARN=lambda_res["FunctionArn"],
        RotationRules={"AutomaticallyAfterDays": 1, "Duration": "1h"},
        RotateImmediately=False,
    )
    assert secret_steps == ["testSecret"]
    secret_steps.clear()


def mock_lambda_zip():
    code = """
        def lambda_handler(event, context):
            return event
        """
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", code)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def create_mock_rotator_lambda():
    client = boto3.client("lambda", region_name="us-east-1")
    return client.create_function(
        FunctionName="mock-rotator",
        Runtime="python3.9",
        Role=get_mock_role_arn(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": mock_lambda_zip()},
    )


def get_mock_role_arn():
    iam = boto3.client("iam", region_name="us-east-1")
    try:
        return iam.get_role(RoleName="my-role")["Role"]["Arn"]
    except ClientError:
        return iam.create_role(
            RoleName="my-role",
            AssumeRolePolicyDocument="some policy",
            Path="/my-path/",
        )["Role"]["Arn"]
