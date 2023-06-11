"""Unit tests for lambda-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_lambda
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from uuid import uuid4
from .utilities import (
    get_role_name,
    get_test_zip_file1,
)

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_lambda
def test_create_alias():
    client = boto3.client("lambda", region_name="ap-southeast-1")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    resp = client.create_alias(
        FunctionName=function_name, Name="alias1", FunctionVersion="$LATEST"
    )

    assert (
        resp["AliasArn"]
        == f"arn:aws:lambda:ap-southeast-1:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert resp["Name"] == "alias1"
    assert resp["FunctionVersion"] == "$LATEST"
    assert resp["Description"] == ""
    assert "RevisionId" in resp
    assert "RoutingConfig" not in resp


@mock_lambda
def test_create_alias_with_routing_config():
    client = boto3.client("lambda", region_name="ap-southeast-1")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    resp = client.create_alias(
        FunctionName=function_name,
        Name="alias1",
        FunctionVersion="$LATEST",
        Description="desc",
        RoutingConfig={"AdditionalVersionWeights": {"2": 0.5}},
    )

    assert resp["Name"] == "alias1"
    assert resp["Description"] == "desc"
    assert resp["RoutingConfig"] == {"AdditionalVersionWeights": {"2": 0.5}}


@mock_lambda
def test_create_alias_using_function_arn():
    client = boto3.client("lambda", region_name="ap-southeast-1")
    function_name = str(uuid4())[0:6]

    fn = client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    fn_arn = fn["FunctionArn"]

    resp = client.create_alias(
        FunctionName=fn_arn, Name="alias1", FunctionVersion="$LATEST"
    )

    assert (
        resp["AliasArn"]
        == f"arn:aws:lambda:ap-southeast-1:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert resp["Name"] == "alias1"
    assert resp["FunctionVersion"] == "$LATEST"


@mock_lambda
def test_delete_alias():
    client = boto3.client("lambda", region_name="us-east-2")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    client.create_alias(
        FunctionName=function_name, Name="alias1", FunctionVersion="$LATEST"
    )

    client.delete_alias(FunctionName=function_name, Name="alias1")

    with pytest.raises(ClientError) as exc:
        client.get_alias(FunctionName=function_name, Name="alias1")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_lambda
def test_get_alias():
    client = boto3.client("lambda", region_name="us-west-1")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    client.create_alias(
        FunctionName=function_name, Name="alias1", FunctionVersion="$LATEST"
    )

    resp = client.get_alias(FunctionName=function_name, Name="alias1")

    assert (
        resp["AliasArn"]
        == f"arn:aws:lambda:us-west-1:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert resp["Name"] == "alias1"
    assert resp["FunctionVersion"] == "$LATEST"
    assert resp["Description"] == ""
    assert "RevisionId" in resp


@mock_lambda
def test_get_alias_using_function_arn():
    client = boto3.client("lambda", region_name="us-west-1")
    function_name = str(uuid4())[0:6]

    fn = client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    fn_arn = fn["FunctionArn"]

    client.create_alias(
        FunctionName=function_name, Name="alias1", FunctionVersion="$LATEST"
    )

    resp = client.get_alias(FunctionName=fn_arn, Name="alias1")

    assert (
        resp["AliasArn"]
        == f"arn:aws:lambda:us-west-1:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert resp["Name"] == "alias1"
    assert resp["FunctionVersion"] == "$LATEST"
    assert resp["Description"] == ""
    assert "RevisionId" in resp


@mock_lambda
def test_get_alias_using_alias_arn():
    client = boto3.client("lambda", region_name="us-west-1")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    alias = client.create_alias(
        FunctionName=function_name, Name="alias1", FunctionVersion="$LATEST"
    )
    alias_arn = alias["AliasArn"]

    resp = client.get_alias(FunctionName=alias_arn, Name="alias1")

    assert (
        resp["AliasArn"]
        == f"arn:aws:lambda:us-west-1:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert resp["Name"] == "alias1"
    assert resp["FunctionVersion"] == "$LATEST"
    assert resp["Description"] == ""
    assert "RevisionId" in resp


@mock_lambda
def test_get_unknown_alias():
    client = boto3.client("lambda", region_name="us-west-1")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    with pytest.raises(ClientError) as exc:
        client.get_alias(FunctionName=function_name, Name="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Cannot find alias arn: arn:aws:lambda:us-west-1:{ACCOUNT_ID}:function:{function_name}:unknown"
    )


@mock_lambda
def test_update_alias():
    client = boto3.client("lambda", region_name="us-east-2")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    client.create_alias(
        FunctionName=function_name, Name="alias1", FunctionVersion="$LATEST"
    )

    resp = client.update_alias(
        FunctionName=function_name,
        Name="alias1",
        FunctionVersion="1",
        Description="updated desc",
    )

    assert (
        resp["AliasArn"]
        == f"arn:aws:lambda:us-east-2:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert resp["Name"] == "alias1"
    assert resp["FunctionVersion"] == "1"
    assert resp["Description"] == "updated desc"
    assert "RevisionId" in resp


@mock_lambda
def test_update_alias_routingconfig():
    client = boto3.client("lambda", region_name="us-east-2")
    function_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    client.create_alias(
        FunctionName=function_name,
        Name="alias1",
        Description="desc",
        FunctionVersion="$LATEST",
    )

    resp = client.update_alias(
        FunctionName=function_name,
        Name="alias1",
        RoutingConfig={"AdditionalVersionWeights": {"2": 0.5}},
    )

    assert (
        resp["AliasArn"]
        == f"arn:aws:lambda:us-east-2:{ACCOUNT_ID}:function:{function_name}:alias1"
    )
    assert resp["Name"] == "alias1"
    assert resp["FunctionVersion"] == "$LATEST"
    assert resp["Description"] == "desc"
    assert resp["RoutingConfig"] == {"AdditionalVersionWeights": {"2": 0.5}}


@mock_lambda
def test_get_function_using_alias():
    client = boto3.client("lambda", region_name="us-east-2")
    fn_name = str(uuid4())[0:6]

    client.create_function(
        FunctionName=fn_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )
    client.publish_version(FunctionName=fn_name)
    client.publish_version(FunctionName=fn_name)

    client.create_alias(FunctionName=fn_name, Name="live", FunctionVersion="1")

    fn = client.get_function(FunctionName=fn_name, Qualifier="live")["Configuration"]
    assert (
        fn["FunctionArn"]
        == f"arn:aws:lambda:us-east-2:{ACCOUNT_ID}:function:{fn_name}:1"
    )
