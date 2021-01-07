import requests
import pytest
import sure  # noqa

import boto3
from moto import mock_sqs, settings


@mock_sqs
@pytest.mark.network
def test_passthrough_requests():
    conn = boto3.client("sqs", region_name="us-west-1")
    conn.create_queue(QueueName="queue1")

    res = requests.get("https://httpbin.org/ip")
    assert res.status_code == 200


if not settings.TEST_SERVER_MODE:

    @mock_sqs
    def test_requests_to_amazon_subdomains_dont_work():
        res = requests.get("https://fakeservice.amazonaws.com/foo/bar")
        assert res.content == b"The method is not implemented"
        assert res.status_code == 400
