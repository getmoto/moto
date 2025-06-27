import os
from tempfile import TemporaryFile

import boto3
import pytest

from . import s3_aws_verified


@pytest.mark.aws_verified
@s3_aws_verified
@pytest.mark.parametrize("encoding", [None, "gzip", "unknown"])
def test_content_encoding_is_returned(encoding, bucket_name=None):
    client = boto3.client("s3", region_name="us-east-1")
    s3_file = "some.file"

    attrs = {
        "ContentType": "application/octet-stream",
        "ACL": "bucket-owner-full-control",
    }
    if encoding:
        attrs["ContentEncoding"] = encoding

    with TemporaryFile() as f:
        f.write(os.urandom(1024))
        f.flush()
        client.upload_fileobj(f, bucket_name, s3_file, ExtraArgs=attrs)

    res = client.get_object(Bucket=bucket_name, Key=s3_file)
    assert res.get("ContentEncoding") == encoding
