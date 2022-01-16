import boto3
import sure  # noqa # pylint: disable=unused-import
import os
import pytest

from moto import mock_s3, settings
from unittest import SkipTest
from unittest.mock import patch


DEFAULT_REGION_NAME = "us-east-1"
CUSTOM_ENDPOINT = "https://s3.local.some-test-domain.de"
CUSTOM_ENDPOINT_2 = "https://caf-o.s3-ext.jc.rl.ac.uk"


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
def test_create_and_list_buckets(url):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    # Have to inline this, as the URL-param is not available as a context decorator
    with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
        # Mock needs to be started after the environment variable is patched in
        with mock_s3():
            bucket = "mybucket"
            conn = boto3.resource("s3", endpoint_url=url)
            conn.create_bucket(Bucket=bucket)

            s3 = boto3.client("s3", endpoint_url=url)
            all_buckets = s3.list_buckets()["Buckets"]
            [b["Name"] for b in all_buckets].should.contain(bucket)


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
def test_create_and_list_buckets_with_multiple_supported_endpoints(url):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    # Have to inline this, as the URL-param is not available as a context decorator
    with patch.dict(
        os.environ,
        {"MOTO_S3_CUSTOM_ENDPOINTS": f"{CUSTOM_ENDPOINT},{CUSTOM_ENDPOINT_2}"},
    ):
        # Mock needs to be started after the environment variable is patched in
        with mock_s3():
            bucket = "mybucket"
            conn = boto3.resource("s3", endpoint_url=url)
            conn.create_bucket(Bucket=bucket)

            s3 = boto3.client("s3", endpoint_url=url)
            all_buckets = s3.list_buckets()["Buckets"]
            [b["Name"] for b in all_buckets].should.contain(bucket)


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
@mock_s3
def test_put_and_get_object(url):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
        with mock_s3():
            bucket = "mybucket"
            key = "file.txt"
            contents = "file contents"
            conn = boto3.resource("s3", endpoint_url=url)
            conn.create_bucket(Bucket=bucket)

            s3 = boto3.client("s3", endpoint_url=url)
            s3.put_object(Bucket=bucket, Key=key, Body=contents)

            body = conn.Object(bucket, key).get()["Body"].read().decode()

            body.should.equal(contents)


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
@mock_s3
def test_put_and_list_objects(url):
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
        with mock_s3():
            bucket = "mybucket"

            s3 = boto3.client("s3", endpoint_url=url)
            s3.create_bucket(Bucket=bucket)
            s3.put_object(Bucket=bucket, Key="one", Body=b"1")
            s3.put_object(Bucket=bucket, Key="two", Body=b"22")
            s3.put_object(Bucket=bucket, Key="three", Body=b"333")

            contents = s3.list_objects(Bucket=bucket)["Contents"]
            contents.should.have.length_of(3)
            [c["Key"] for c in contents].should.contain("two")
