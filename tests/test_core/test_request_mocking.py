import requests
import pytest
import sure  # noqa # pylint: disable=unused-import

import boto3
from moto import mock_s3, mock_sts, mock_sqs, settings


@mock_sqs
@pytest.mark.network
def test_passthrough_requests() -> None:
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")

    res = requests.get("https://google.com/")
    assert res.status_code < 400


if not settings.TEST_SERVER_MODE:

    @mock_sqs
    def test_requests_to_amazon_subdomains_dont_work() -> None:
        res = requests.get("https://fakeservice.amazonaws.com/foo/bar")
        assert res.content == b"The method is not implemented"
        assert res.status_code == 400


@mock_sts
@mock_s3
def test_decorator_ordering() -> None:
    """
    https://github.com/spulec/moto/issues/3790#issuecomment-803979809
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
    resp.status_code.should.equal(200)  # type: ignore[attr-defined]
