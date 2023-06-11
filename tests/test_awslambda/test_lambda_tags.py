import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_lambda, mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from uuid import uuid4
from .utilities import get_role_name, get_test_zip_file2

_lambda_region = "us-east-1"
boto3.setup_default_session(region_name=_lambda_region)


@mock_lambda
@mock_s3
def test_tags():
    """
    test list_tags -> tag_resource -> list_tags -> tag_resource -> list_tags -> untag_resource -> list_tags integration
    """
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(Bucket=bucket_name)

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    function = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    # List tags when there are none
    assert conn.list_tags(Resource=function["FunctionArn"])["Tags"] == dict()

    # List tags when there is one
    resp = conn.tag_resource(Resource=function["FunctionArn"], Tags={"spam": "eggs"})
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert conn.list_tags(Resource=function["FunctionArn"])["Tags"] == {"spam": "eggs"}

    # List tags when another has been added
    resp = conn.tag_resource(Resource=function["FunctionArn"], Tags=dict(foo="bar"))
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert conn.list_tags(Resource=function["FunctionArn"])["Tags"] == {
        "spam": "eggs",
        "foo": "bar",
    }

    # Untag resource
    resp = conn.untag_resource(
        Resource=function["FunctionArn"], TagKeys=["spam", "trolls"]
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204
    assert conn.list_tags(Resource=function["FunctionArn"])["Tags"] == {"foo": "bar"}

    # Untag a tag that does not exist (no error and no change)
    resp = conn.untag_resource(Resource=function["FunctionArn"], TagKeys=["spam"])
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204


@mock_lambda
@mock_s3
def test_create_function_with_tags():
    bucket_name = str(uuid4())
    s3_conn = boto3.client("s3", _lambda_region)
    s3_conn.create_bucket(Bucket=bucket_name)

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket=bucket_name, Key="test.zip", Body=zip_content)
    conn = boto3.client("lambda", _lambda_region)
    function_name = str(uuid4())[0:6]

    function = conn.create_function(
        FunctionName=function_name,
        Runtime="python2.7",
        Role=get_role_name(),
        Handler="lambda_function.handler",
        Code={"S3Bucket": bucket_name, "S3Key": "test.zip"},
        Tags={"key1": "val1", "key2": "val2"},
    )

    tags = conn.list_tags(Resource=function["FunctionArn"])["Tags"]
    assert tags == {"key1": "val1", "key2": "val2"}

    result = conn.get_function(FunctionName=function_name)
    assert result["Tags"] == {"key1": "val1", "key2": "val2"}


@mock_lambda
def test_tags_not_found():
    """
    Test list_tags and tag_resource when the lambda with the given arn does not exist
    """
    conn = boto3.client("lambda", _lambda_region)
    with pytest.raises(ClientError):
        conn.list_tags(Resource=f"arn:aws:lambda:{ACCOUNT_ID}:function:not-found")

    with pytest.raises(ClientError):
        conn.tag_resource(
            Resource=f"arn:aws:lambda:{ACCOUNT_ID}:function:not-found",
            Tags=dict(spam="eggs"),
        )

    with pytest.raises(ClientError):
        conn.untag_resource(
            Resource=f"arn:aws:lambda:{ACCOUNT_ID}:function:not-found",
            TagKeys=["spam"],
        )
