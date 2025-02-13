from unittest import SkipTest

import boto3
import pytest
import requests
from responses import Response

from moto import mock_aws, settings
from moto.core.models import responses_mock


@mock_aws
@pytest.mark.network
def test_passthrough_requests() -> None:
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")

    res = requests.get("https://google.com/")
    assert res.status_code < 400


if not settings.TEST_SERVER_MODE:

    @mock_aws
    def test_requests_to_amazon_subdomains_dont_work() -> None:
        res = requests.get("https://fakeservice.amazonaws.com/foo/bar")
        assert res.content == b"The method is not implemented"
        assert res.status_code == 400


@mock_aws
def test_decorator_ordering() -> None:
    """
    https://github.com/getmoto/moto/issues/3790#issuecomment-803979809
    """
    bucket_name = "banana-slugs"
    key = "trash-file"
    region = "us-east-1"
    client = boto3.client("s3", region_name=region)
    s3 = boto3.resource("s3", region_name=region)
    bucket = s3.Bucket(bucket_name)
    bucket.create()
    bucket.put_object(Body=b"ABCD", Key=key)
    presigned_url = client.generate_presigned_url(
        ClientMethod=client.get_object.__name__,
        Params={
            "Bucket": bucket_name,
            "Key": key,
            "ResponseContentDisposition": "attachment;filename=bar",
        },
    )

    resp = requests.get(presigned_url)
    assert resp.status_code == 200


@mock_aws()
def test_replace_and_remove_mock() -> None:
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Only need to test responses mock in decorator mode")
    rsp1 = Response(method="GET", url="http://example.com", body="test")
    responses_mock.add(rsp1)

    assert requests.get("http://example.com/").text == "test"

    rsp2 = Response(method="GET", url="http://example.com", body="test2")
    responses_mock.replace(rsp2)

    assert requests.get("http://example.com/").text == "test2"

    responses_mock.remove("GET", "https://example.com/")
