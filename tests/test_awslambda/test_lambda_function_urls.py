import sys
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.utilities.distutils_version import LooseVersion

from .utilities import get_role_name, get_test_zip_file1

PYTHON_VERSION = "python3.11"

boto3_version = sys.modules["botocore"].__version__


@mock_aws
@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
def test_create_function_url_config(key):
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    client = boto3.client("lambda", "us-east-2")
    function_name = str(uuid4())[0:6]
    fxn = client.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    name_or_arn = fxn[key]

    resp = client.create_function_url_config(
        AuthType="AWS_IAM", FunctionName=name_or_arn
    )
    assert resp["FunctionArn"] == fxn["FunctionArn"]
    assert resp["AuthType"] == "AWS_IAM"
    assert "FunctionUrl" in resp

    resp = client.get_function_url_config(FunctionName=name_or_arn)
    assert resp["FunctionArn"] == fxn["FunctionArn"]
    assert resp["AuthType"] == "AWS_IAM"
    assert "FunctionUrl" in resp


@mock_aws
def test_create_function_url_config_with_cors():
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    client = boto3.client("lambda", "us-east-2")
    function_name = str(uuid4())[0:6]
    fxn = client.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    name_or_arn = fxn["FunctionName"]

    resp = client.create_function_url_config(
        AuthType="AWS_IAM",
        FunctionName=name_or_arn,
        Cors={
            "AllowCredentials": True,
            "AllowHeaders": ["date", "keep-alive"],
            "AllowMethods": ["*"],
            "AllowOrigins": ["*"],
            "ExposeHeaders": ["date", "keep-alive"],
            "MaxAge": 86400,
        },
    )
    assert resp["Cors"] == {
        "AllowCredentials": True,
        "AllowHeaders": ["date", "keep-alive"],
        "AllowMethods": ["*"],
        "AllowOrigins": ["*"],
        "ExposeHeaders": ["date", "keep-alive"],
        "MaxAge": 86400,
    }


@mock_aws
def test_update_function_url_config_with_cors():
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    client = boto3.client("lambda", "us-east-2")
    function_name = str(uuid4())[0:6]
    fxn = client.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    name_or_arn = fxn["FunctionName"]

    resp = client.create_function_url_config(
        AuthType="AWS_IAM",
        FunctionName=name_or_arn,
        Cors={
            "AllowCredentials": True,
            "AllowHeaders": ["date", "keep-alive"],
            "AllowMethods": ["*"],
            "AllowOrigins": ["*"],
            "ExposeHeaders": ["date", "keep-alive"],
            "MaxAge": 86400,
        },
    )

    resp = client.update_function_url_config(
        FunctionName=name_or_arn, AuthType="NONE", Cors={"AllowCredentials": False}
    )
    assert resp["Cors"] == {"AllowCredentials": False}


@mock_aws
@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
def test_delete_function_url_config(key):
    if LooseVersion(boto3_version) < LooseVersion("1.29.0"):
        raise SkipTest("Parameters only available in newer versions")
    client = boto3.client("lambda", "us-east-2")
    function_name = str(uuid4())[0:6]
    fxn = client.create_function(
        FunctionName=function_name,
        Runtime=PYTHON_VERSION,
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    name_or_arn = fxn[key]

    client.create_function_url_config(AuthType="AWS_IAM", FunctionName=name_or_arn)

    client.delete_function_url_config(FunctionName=name_or_arn)

    # It no longer exists
    with pytest.raises(ClientError):
        client.get_function_url_config(FunctionName=name_or_arn)
