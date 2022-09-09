import botocore.client
import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_lambda, mock_s3
from moto.core.models import ACCOUNT_ID
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
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(dict())

    # List tags when there is one
    conn.tag_resource(Resource=function["FunctionArn"], Tags=dict(spam="eggs"))[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(200)
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(
        dict(spam="eggs")
    )

    # List tags when another has been added
    conn.tag_resource(Resource=function["FunctionArn"], Tags=dict(foo="bar"))[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(200)
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(
        dict(spam="eggs", foo="bar")
    )

    # Untag resource
    conn.untag_resource(Resource=function["FunctionArn"], TagKeys=["spam", "trolls"])[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(204)
    conn.list_tags(Resource=function["FunctionArn"])["Tags"].should.equal(
        dict(foo="bar")
    )

    # Untag a tag that does not exist (no error and no change)
    conn.untag_resource(Resource=function["FunctionArn"], TagKeys=["spam"])[
        "ResponseMetadata"
    ]["HTTPStatusCode"].should.equal(204)


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
    tags.should.equal({"key1": "val1", "key2": "val2"})

    result = conn.get_function(FunctionName=function_name)
    result.should.have.key("Tags").equals({"key1": "val1", "key2": "val2"})


@mock_lambda
def test_tags_not_found():
    """
    Test list_tags and tag_resource when the lambda with the given arn does not exist
    """
    conn = boto3.client("lambda", _lambda_region)
    conn.list_tags.when.called_with(
        Resource="arn:aws:lambda:{}:function:not-found".format(ACCOUNT_ID)
    ).should.throw(botocore.client.ClientError)

    conn.tag_resource.when.called_with(
        Resource="arn:aws:lambda:{}:function:not-found".format(ACCOUNT_ID),
        Tags=dict(spam="eggs"),
    ).should.throw(botocore.client.ClientError)

    conn.untag_resource.when.called_with(
        Resource="arn:aws:lambda:{}:function:not-found".format(ACCOUNT_ID),
        TagKeys=["spam"],
    ).should.throw(botocore.client.ClientError)
