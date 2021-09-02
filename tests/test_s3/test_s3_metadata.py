import boto3

from moto import mock_s3
from moto.s3.responses import DEFAULT_REGION_NAME

import sure  # noqa


@mock_s3
def test_s3_returns_requestid():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    resp = s3.create_bucket(Bucket="mybucket")
    _check_metadata(resp)

    resp = s3.put_object(Bucket="mybucket", Key="steve", Body=b"is awesome")
    _check_metadata(resp)

    resp = s3.get_object(Bucket="mybucket", Key="steve")
    _check_metadata(resp)


def _check_metadata(resp):
    meta = resp["ResponseMetadata"]
    headers = meta["HTTPHeaders"]
    meta.should.have.key("RequestId")
    headers.should.have.key("x-amzn-requestid")
    meta["RequestId"].should.equal(headers["x-amzn-requestid"])
