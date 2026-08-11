from unittest import SkipTest

import boto3
import pytest
import requests

from moto import settings
from moto.s3.responses import DEFAULT_REGION_NAME
from moto.server import ThreadedMotoServer
from tests import allow_aws_request

from . import s3_aws_verified
from .test_s3 import add_proxy_details


@s3_aws_verified
@pytest.mark.aws_verified
def test_presigned_url_generates_content_response_headers(bucket_name=None):
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket(bucket_name)
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    params = {
        "Bucket": bucket.name,
        "Key": "file.txt",
        "ResponseCacheControl": "max-age=74",
        "ResponseContentDisposition": 'attachment; filename="foo.jpg"',
        "ResponseContentEncoding": "identity",
        "ResponseContentLanguage": "de-DE",
        "ResponseContentType": "image/jpeg",
        "ResponseExpires": "Wed, 21 Oct 2015 07:28:00 GMT",
    }
    presigned_url = client.generate_presigned_url("get_object", params, ExpiresIn=900)
    get_kwargs = {}
    if not allow_aws_request() and settings.is_test_proxy_mode():
        add_proxy_details(get_kwargs)
    response = requests.get(presigned_url, **get_kwargs)

    assert response.content == b"ABCD"

    assert response.headers.get("Cache-Control") == "max-age=74"
    assert (
        response.headers.get("Content-Disposition") == 'attachment; filename="foo.jpg"'
    )
    assert response.headers.get("Content-Encoding") == "identity"
    assert response.headers.get("Content-Language") == "de-DE"
    assert response.headers.get("Content-Type") == "image/jpeg"
    assert response.headers.get("Content-Length") == "4"
    assert response.headers.get("Expires") == "Wed, 21 Oct 2015 07:28:00 GMT"


def test_presigned_url_replaces_stored_content_disposition_in_server_mode():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point testing the ThreadedMotoServer in Server/Proxy-mode")
    server = ThreadedMotoServer(ip_address="127.0.0.1", port=0, verbose=False)
    server.start()
    host, port = server.get_host_and_port()
    try:
        client = boto3.client(
            "s3",
            endpoint_url=f"http://{host}:{port}",
            region_name=DEFAULT_REGION_NAME,
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )
        client.create_bucket(Bucket="header-override-test")
        client.put_object(
            Bucket="header-override-test",
            Key="file.txt",
            Body=b"ABCD",
            ContentDisposition='inline; filename="stored.txt"',
        )

        presigned_url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": "header-override-test",
                "Key": "file.txt",
                "ResponseContentDisposition": 'attachment; filename="download.txt"',
            },
        )
        response = requests.get(presigned_url)

        assert response.raw.headers.getlist("Content-Disposition") == [
            'attachment; filename="download.txt"'
        ]
    finally:
        server.stop()
