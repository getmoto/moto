import boto3
import pytest

from . import s3_aws_verified
from .test_s3 import DEFAULT_REGION_NAME


@pytest.mark.aws_verified
@s3_aws_verified
def test_header_content_type(bucket_name=None):
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    resp = client.list_buckets()
    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    assert headers.get("content-type") == "application/xml"

    resp = client.list_object_versions(Bucket=bucket_name)
    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    assert headers.get("content-type") == "application/xml"

    resp = client.head_bucket(Bucket=bucket_name)
    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    assert headers.get("content-type") == "application/xml"

    resp = client.put_object(Bucket=bucket_name, Key="key", Body=b"data")
    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    # Werkzeug automatically adds a content-type if none is specified
    assert headers.get("content-type") in [None, "text/html; charset=utf-8"]

    resp = client.get_object(Bucket=bucket_name, Key="key")
    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    assert headers.get("content-type") == "binary/octet-stream"
