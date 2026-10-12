from uuid import uuid4

import boto3

from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME


@mock_aws
def test_s3_metadata_keys_with_underscores():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="probe-bucket")
    s3.put_object(
        Bucket="probe-bucket",
        Key="k",
        Body=b"x",
        Metadata={"transform_watermark": "t", "source": "s"},
    )
    resp = s3.get_object(Bucket="probe-bucket", Key="k")
    metadata = resp["Metadata"]
    assert metadata["transform_watermark"] == "t"


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
