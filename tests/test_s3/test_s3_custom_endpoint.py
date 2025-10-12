import os
from unittest import SkipTest
from unittest.mock import patch

import boto3
import pytest
import requests

from moto import mock_aws, settings

DEFAULT_REGION_NAME = "us-east-1"
CUSTOM_ENDPOINT = "https://s3.local.some-test-domain.de"
CUSTOM_ENDPOINT_2 = "https://caf-o.s3-ext.jc.rl.ac.uk"


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
def test_create_and_list_buckets(url):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    # Have to inline this, as the URL-param is not available as a context decorator
    with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
        # Mock needs to be started after the environment variable is patched in
        with mock_aws():
            bucket = "mybucket"
            conn = boto3.resource(
                "s3", endpoint_url=url, region_name=DEFAULT_REGION_NAME
            )
            conn.create_bucket(Bucket=bucket)

            s3_client = boto3.client("s3", endpoint_url=url)
            all_buckets = s3_client.list_buckets()["Buckets"]
            assert bucket in [b["Name"] for b in all_buckets]


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
def test_create_and_list_buckets_with_multiple_supported_endpoints(url):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    # Have to inline this, as the URL-param is not available as a context decorator
    with patch.dict(
        os.environ,
        {"MOTO_S3_CUSTOM_ENDPOINTS": f"{CUSTOM_ENDPOINT},{CUSTOM_ENDPOINT_2}"},
    ):
        # Mock needs to be started after the environment variable is patched in
        with mock_aws():
            bucket = "mybucket"
            conn = boto3.resource(
                "s3", endpoint_url=url, region_name=DEFAULT_REGION_NAME
            )
            conn.create_bucket(Bucket=bucket)

            s3_client = boto3.client("s3", endpoint_url=url)
            all_buckets = s3_client.list_buckets()["Buckets"]
            assert bucket in [b["Name"] for b in all_buckets]


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
@mock_aws
def test_put_and_get_object(url):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
        with mock_aws():
            bucket = "mybucket"
            key = "file.txt"
            contents = "file contents"
            conn = boto3.resource(
                "s3", endpoint_url=url, region_name=DEFAULT_REGION_NAME
            )
            conn.create_bucket(Bucket=bucket)

            s3_client = boto3.client("s3", endpoint_url=url)
            s3_client.put_object(Bucket=bucket, Key=key, Body=contents)

            body = conn.Object(bucket, key).get()["Body"].read().decode()

            assert body == contents


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
@mock_aws
def test_put_and_list_objects(url):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
        with mock_aws():
            bucket = "mybucket"

            s3_client = boto3.client(
                "s3", endpoint_url=url, region_name=DEFAULT_REGION_NAME
            )
            s3_client.create_bucket(Bucket=bucket)
            s3_client.put_object(Bucket=bucket, Key="one", Body=b"1")
            s3_client.put_object(Bucket=bucket, Key="two", Body=b"22")
            s3_client.put_object(Bucket=bucket, Key="three", Body=b"333")

            contents = s3_client.list_objects(Bucket=bucket)["Contents"]
            assert len(contents) == 3
            assert "two" in [c["Key"] for c in contents]


@pytest.mark.parametrize("url", [CUSTOM_ENDPOINT, CUSTOM_ENDPOINT_2])
def test_get_presigned_url(url):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Unable to set ENV VAR in ServerMode")
    with patch.dict(os.environ, {"MOTO_S3_CUSTOM_ENDPOINTS": url}):
        with mock_aws():
            bucket = "mybucket"
            key = "file.txt"
            contents = b"file contents"
            conn = boto3.resource(
                "s3", endpoint_url=url, region_name=DEFAULT_REGION_NAME
            )
            conn.create_bucket(Bucket=bucket)

            s3_client = boto3.client("s3", endpoint_url=url)
            s3_client.put_object(Bucket=bucket, Key=key, Body=contents)

            signed_url = s3_client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=86400
            )
            response = requests.get(signed_url, stream=False)
            assert contents == response.content
