from uuid import uuid4

import boto3

from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME


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
