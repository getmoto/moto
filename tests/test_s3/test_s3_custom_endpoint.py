import boto3
from botocore.config import Config

from moto import mock_s3
import sure  # noqa
import os
import unittest


DEFAULT_REGION_NAME = "us-east-1"
CUSTOM_ENDPOINT = "https://s3.local.some-test-domain.de"

config = Config(connect_timeout=2, retries={"max_attempts": 1, "mode": "standard"})
s3_kwargs = {
    "region_name": DEFAULT_REGION_NAME,
    "endpoint_url": CUSTOM_ENDPOINT,
    "config": config,
}


class S3CustomEndpointTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["CUSTOM_ENDPOINTS"] = CUSTOM_ENDPOINT

    def tearDown(self):
        del os.environ["CUSTOM_ENDPOINTS"]

    @mock_s3
    def test_create_and_list_buckets(self):
        bucket = "mybucket"
        conn = boto3.resource("s3", **s3_kwargs)
        conn.create_bucket(Bucket=bucket)

        s3 = boto3.client("s3", **s3_kwargs)
        all_buckets = s3.list_buckets()["Buckets"]
        [b["Name"] for b in all_buckets].should.contain(bucket)

    @mock_s3
    def test_put_and_get_object(self):
        bucket = "mybucket"
        key = "file.txt"
        contents = "file contents"
        conn = boto3.resource("s3", **s3_kwargs)
        conn.create_bucket(Bucket=bucket)

        s3 = boto3.client("s3", **s3_kwargs)
        s3.put_object(Bucket=bucket, Key=key, Body=contents)

        body = conn.Object(bucket, key).get()["Body"].read().decode()

        body.should.equal(contents)

    @mock_s3
    def test_put_and_list_objects(self):
        bucket = "mybucket"

        s3 = boto3.client("s3", **s3_kwargs)
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket, Key="one", Body=b"1")
        s3.put_object(Bucket=bucket, Key="two", Body=b"22")
        s3.put_object(Bucket=bucket, Key="three", Body=b"333")

        contents = s3.list_objects(Bucket=bucket)["Contents"]
        contents.should.have.length_of(3)
        [c["Key"] for c in contents].should.contain("two")
