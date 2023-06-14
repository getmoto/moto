import boto3
import json
import pytest

from botocore.exceptions import ClientError
from moto import mock_lambda, mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from uuid import uuid4
from .utilities import get_role_name, get_test_zip_file1, get_test_zip_file2

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
    )
    name_or_arn = f[key]

    response = conn.add_permission(
        FunctionName=name_or_arn,
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
    )
    assert "Statement" in response
    res = json.loads(response["Statement"])
    assert res["Action"] == "lambda:InvokeFunction"
    assert res["Condition"] == {
        "ArnLike": {
            "AWS:SourceArn": "arn:aws:lambda:us-west-2:account-id:function:helloworld"
        }
    }


@mock_lambda
def test_add_permission_with_principalorgid():
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    fn_arn = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=(get_role_name()),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
    )["FunctionArn"]

    source_arn = "arn:aws:lambda:us-west-2:account-id:function:helloworld"
    response = conn.add_permission(
        FunctionName=fn_arn,
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        PrincipalOrgID="o-a1b2c3d4e5",
        SourceArn=source_arn,
    )
    assert "Statement" in response
    res = json.loads(response["Statement"])

    assert res["Condition"]["StringEquals"] == {"aws:PrincipalOrgID": "o-a1b2c3d4e5"}
    assert res["Condition"]["ArnLike"] == {"AWS:SourceArn": source_arn}
    assert "PrincipalOrgID" not in res


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
        StatementId="2",
        Action="lambda:InvokeFunction",
        Principal="lambda.amazonaws.com",
        SourceArn=f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:helloworld",
    )

    response = conn.get_policy(FunctionName=name_or_arn)

    assert "Policy" in response
    res = json.loads(response["Policy"])
    assert res["Statement"][0]["Action"] == "lambda:InvokeFunction"
    assert res["Statement"][0]["Principal"] == {"Service": "lambda.amazonaws.com"}
    assert (
        res["Statement"][0]["Resource"]
        == f"arn:aws:lambda:us-west-2:123456789012:function:{function_name}"
    )


@mock_lambda
def test_get_policy_with_qualifier():
    # assert that the resource within the statement ends with :qualifier
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    zip_content_two = get_test_zip_file2()

    conn.update_function_code(
        FunctionName=function_name, ZipFile=zip_content_two, Publish=True
    )

    conn.add_permission(
        FunctionName=function_name,
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="lambda.amazonaws.com",
        SourceArn=f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:helloworld",
        Qualifier="2",
    )

    response = conn.get_policy(FunctionName=function_name, Qualifier="2")

    assert "Policy" in response
    res = json.loads(response["Policy"])
    assert res["Statement"][0]["Action"] == "lambda:InvokeFunction"
    assert res["Statement"][0]["Principal"] == {"Service": "lambda.amazonaws.com"}
    assert (
        res["Statement"][0]["Resource"]
        == f"arn:aws:lambda:us-west-2:123456789012:function:{function_name}:2"
    )


@mock_lambda
def test_add_permission_with_unknown_qualifier():
    # assert that the resource within the statement ends with :qualifier
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    conn.create_function(
        FunctionName=function_name,
        Runtime="python3.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"ZipFile": zip_content},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    with pytest.raises(ClientError) as exc:
        conn.add_permission(
            FunctionName=function_name,
            StatementId="2",
            Action="lambda:InvokeFunction",
            Principal="lambda.amazonaws.com",
            SourceArn=f"arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:helloworld",
            Qualifier="5",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Function not found: arn:aws:lambda:us-west-2:{ACCOUNT_ID}:function:{function_name}:5"
    )


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
    )
    name_or_arn = f[key]

    conn.add_permission(
        FunctionName=name_or_arn,
        StatementId="1",
        Action="lambda:InvokeFunction",
        Principal="432143214321",
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
    )

    remove = conn.remove_permission(FunctionName=name_or_arn, StatementId="1")
    assert remove["ResponseMetadata"]["HTTPStatusCode"] == 204
    policy = conn.get_policy(FunctionName=name_or_arn)["Policy"]
    policy = json.loads(policy)
    assert policy["Statement"] == []


@pytest.mark.parametrize("key", ["FunctionName", "FunctionArn"])
@mock_lambda
def test_remove_function_permission__with_qualifier(key):
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

    # Ensure Qualifier=2 exists
    zip_content_two = get_test_zip_file2()
    conn.update_function_code(
        FunctionName=function_name, ZipFile=zip_content_two, Publish=True
    )

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
    assert remove["ResponseMetadata"]["HTTPStatusCode"] == 204
    policy = conn.get_policy(FunctionName=name_or_arn, Qualifier="2")["Policy"]
    policy = json.loads(policy)
    assert policy["Statement"] == []


@mock_lambda
@mock_s3
def test_get_unknown_policy():
    conn = boto3.client("lambda", _lambda_region)

    with pytest.raises(ClientError) as exc:
        conn.get_policy(FunctionName="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == "Function not found: arn:aws:lambda:us-west-2:123456789012:function:unknown"
    )
