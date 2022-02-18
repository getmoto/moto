"""
Ensure that the responses module plays nice with our mocks
"""

from moto import mock_s3
import requests
import responses
from requests.auth import HTTPBasicAuth
from responses import matchers
import boto3
from unittest.mock import patch
import os
from freezegun import freeze_time


@patch.dict(
    os.environ,
    {
        "HTTP_PROXY": "http://127.0.0.1",
        "HTTPS_PROXY": "http://127.0.0.2",
        "AWS_DEFAULT_REGION": "us-east-1",
    },
)
@mock_s3
@responses.activate
@freeze_time("1.1.1970")
def test_moto_first():
    moto_responses_compatibility()


@responses.activate
@mock_s3
def test_moto_second():
    moto_responses_compatibility()


def moto_responses_compatibility():
    responses.add(
        responses.GET,
        url="http://127.0.0.1/lkdsfjlkdsa",
        json={"a": "4"},
        match=[
            matchers.request_kwargs_matcher({"stream": False, "verify": False}),
            matchers.header_matcher({"Accept": "text/plain", "magic": "a"}),
        ],
    )
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="mybucket")
    s3.put_object(Bucket="mybucket", Key="name", Body="value")
    s3.get_object(Bucket="mybucket", Key="name")["Body"].read()
    with requests.get(
        "http://127.0.0.1/lkdsfjlkdsa",
        headers={"Accept": "text/plain", "magic": "a"},
        auth=HTTPBasicAuth("a", "b"),
        verify=False,
    ) as r:
        r.raise_for_status()
        assert r.json() == {"a": "4"}
