import datetime

import boto3
import botocore.exceptions
import pytest
from botocore.client import ClientError

from moto import mock_aws
from moto.core.utils import utcnow
from moto.s3.responses import DEFAULT_REGION_NAME

from . import s3_aws_verified
from .test_s3 import enable_versioning


@mock_aws
def test_head_object_if_modified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=utcnow() + datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_head_object_if_modified_since_refresh():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    response = s3_client.head_object(Bucket=bucket_name, Key=key)

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=response["LastModified"],
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_head_object_if_unmodified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(
            Bucket=bucket_name,
            Key=key,
            IfUnmodifiedSince=utcnow() - datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"] == {
        "Code": "412",
        "Message": "Precondition Failed",
    }


@mock_aws
def test_head_object_if_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(Bucket=bucket_name, Key=key, IfMatch='"hello"')
    err_value = err.value
    assert err_value.response["Error"] == {
        "Code": "412",
        "Message": "Precondition Failed",
    }


@mock_aws
def test_head_object_if_none_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.head_object(Bucket=bucket_name, Key=key, IfNoneMatch=etag)
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}
    assert err_value.response["ResponseMetadata"]["HTTPHeaders"]["etag"] == etag


@mock_aws
def test_get_object_if_modified_since_refresh():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    response = s3_client.get_object(Bucket=bucket_name, Key=key)

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=response["LastModified"],
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_get_object_if_modified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(
            Bucket=bucket_name,
            Key=key,
            IfModifiedSince=utcnow() + datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}


@mock_aws
def test_get_object_if_unmodified_since():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(
            Bucket=bucket_name,
            Key=key,
            IfUnmodifiedSince=utcnow() - datetime.timedelta(hours=1),
        )
    err_value = err.value
    assert err_value.response["Error"]["Code"] == "PreconditionFailed"
    assert err_value.response["Error"]["Condition"] == "If-Unmodified-Since"


@mock_aws
def test_get_object_if_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(Bucket=bucket_name, Key=key, IfMatch='"hello"')
    err_value = err.value
    assert err_value.response["Error"]["Code"] == "PreconditionFailed"
    assert err_value.response["Error"]["Condition"] == "If-Match"


@mock_aws
def test_get_object_if_none_match():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "blah"
    s3_client.create_bucket(Bucket=bucket_name)

    key = "hello.txt"

    etag = s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")["ETag"]

    with pytest.raises(botocore.exceptions.ClientError) as err:
        s3_client.get_object(Bucket=bucket_name, Key=key, IfNoneMatch=etag)
    err_value = err.value
    assert err_value.response["Error"] == {"Code": "304", "Message": "Not Modified"}
    assert err_value.response["ResponseMetadata"]["HTTPHeaders"]["etag"] == etag


@s3_aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize("versioned", [True, False], ids=["versioned", "not versioned"])
def test_put_object_if_none_match(versioned, bucket_name=None):
    s3 = boto3.client("s3", region_name="us-east-1")
    if versioned:
        enable_versioning(bucket_name, s3)

    s3.put_object(
        Key="test_object",
        Body="test",
        Bucket=bucket_name,
        IfNoneMatch="*",
    )

    with pytest.raises(ClientError) as exc:
        s3.put_object(
            Key="test_object",
            Body="another_test",
            Bucket=bucket_name,
            IfNoneMatch="*",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "PreconditionFailed"
    assert (
        err["Message"]
        == "At least one of the pre-conditions you specified did not hold"
    )
    assert err["Condition"] == "If-None-Match"


@s3_aws_verified
@pytest.mark.aws_verified
def test_put_object_if_match(bucket_name=None):
    s3 = boto3.client("s3", region_name="us-east-1")
    etag = s3.put_object(Bucket=bucket_name, Key="test_key", Body=b"test")["ETag"]

    with pytest.raises(ClientError) as exc:
        s3.put_object(Bucket=bucket_name, Key="test_key", Body=b"test2", IfMatch="test")
    err = exc.value.response["Error"]
    assert err["Code"] == "PreconditionFailed"
    assert (
        err["Message"]
        == "At least one of the pre-conditions you specified did not hold"
    )
    assert err["Condition"] == "If-Match"

    # We can if we match the etag
    etag2 = s3.put_object(
        Bucket=bucket_name, Key="test_key", Body=b"test2", IfMatch=etag
    )["ETag"]
    assert etag != etag2

    # S3 is flexible - it will accept ETags without quotes
    etag_without_quotes = etag2.replace('"', "")
    etag3 = s3.put_object(
        Bucket=bucket_name, Key="test_key", Body=b"test3", IfMatch=etag_without_quotes
    )["ETag"]

    # And ETags with one quote removed
    s3.put_object(Bucket=bucket_name, Key="test_key", Body=b"test4", IfMatch=etag3[1:])

    # It will fail when specifying an unknown key though
    with pytest.raises(ClientError) as exc:
        s3.put_object(Bucket=bucket_name, Key="unknown", Body=b"test", IfMatch="test")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchKey"
