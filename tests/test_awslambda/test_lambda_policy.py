import boto3
import json
import sure  # noqa # pylint: disable=unused-import
import pytest

from botocore.exceptions import ClientError
from moto import mock_lambda, mock_s3
from uuid import uuid4
from .utilities import get_role_name, get_test_zip_file1

_lambda_region = "us-west-2"
boto3.setup_default_session(region_name=_lambda_region)


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
def test_add_function_permission(key):
    """
    Parametrized to ensure that we can add permission by using the FunctionName and the FunctionArn
    """
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    f = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = f[key]

    response = conn.add_permission(
        FunctionName=name_or_arn,
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount="123412341234",
        EventSourceToken="blah",
        Qualifier="2",
    )
    assert "Statement" in response
    res = json.loads(response["Statement"])
    assert res["Action"] == "lambda:InvokeFunction"


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
def test_get_function_policy(key):
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    f = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = f[key]

    conn.add_permission(
        FunctionName=name_or_arn,
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount="123412341234",
        EventSourceToken="blah",
        Qualifier="2",
    )

    response = conn.get_policy(FunctionName=name_or_arn)

    assert "Policy" in response
    res = json.loads(response["Policy"])
    assert res["Statement"][0]["Action"] == "lambda:InvokeFunction"


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
def test_remove_function_permission(key):
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    f = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    name_or_arn = f[key]

    conn.add_permission(
        FunctionName=name_or_arn,
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount="123412341234",
        EventSourceToken="blah",
        Qualifier="2",
    )

    remove = conn.remove_permission(
        FunctionName=name_or_arn, StatementId="1", Qualifier="2"
    )
    remove["ResponseMetadata"]["HTTPStatusCode"].should.equal(204)
    policy = conn.get_policy(FunctionName=name_or_arn, Qualifier="2")["Policy"]
    policy = json.loads(policy)
    policy["Statement"].should.equal([])


@mock_lambda
@mock_s3
def test_get_unknown_policy():
    conn = boto3.client("lambda", _lambda_region)

    with pytest.raises(ClientError) as exc:
        conn.get_policy(FunctionName="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("Function not found: unknown")
