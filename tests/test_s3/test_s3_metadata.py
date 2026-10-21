from uuid import uuid4

import boto3
import pytest

from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME

from . import s3_aws_verified


@s3_aws_verified
@pytest.mark.aws_verified
def test_s3_metadata_keys_with_underscores(bucket_name=None):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.put_object(
        Bucket=bucket_name,
        Key="test-key",
        Body=b"x",
        Metadata={
            "transform_watermark": "t",
            "no-underscore": "s",
            "has_underscore": "h",
        },
    )
    resp = s3.get_object(Bucket=bucket_name, Key="test-key")
    metadata = resp["Metadata"]
    assert metadata["transform_watermark"] == "t"
    assert metadata["no-underscore"] == "s"
    assert metadata["has_underscore"] == "h"
    resp = s3.head_object(Bucket=bucket_name, Key="test-key")
    metadata = resp["Metadata"]
    assert metadata["transform_watermark"] == "t"
    assert metadata["no-underscore"] == "s"
    assert metadata["has_underscore"] == "h"


@mock_aws
def test_s3_returns_requestid():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = str(uuid4())
    resp = s3_client.create_bucket(Bucket=bucket_name)
    _check_metadata(resp)

    resp = s3_client.put_object(Bucket=bucket_name, Key="steve", Body=b"is awesome")
    _check_metadata(resp)

    resp = s3_client.get_object(Bucket=bucket_name, Key="steve")
    _check_metadata(resp)


def _check_metadata(resp):
    meta = resp["ResponseMetadata"]
    headers = meta["HTTPHeaders"]
    assert "RequestId" in meta
    assert "x-amzn-requestid" in headers
    assert meta["RequestId"] == headers["x-amzn-requestid"]
