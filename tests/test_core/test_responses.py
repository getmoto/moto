import datetime
from gzip import compress as gzip_compress

from freezegun import freeze_time

from moto import settings
from moto.core.request import Request
from moto.core.responses import BaseResponse
from moto.s3.responses import S3Response

HTTPHeaders = dict


def mock_request(
    method: str, url: str, headers: dict[str, str], body: bytes | None
) -> Request:
    return Request.from_primitives(method, url, headers, body)


def test_parse_qs_unicode_decode_error() -> None:
    body = b'{"key": "%D0"}, "C": "#0 = :0"}'
    headers = HTTPHeaders()
    headers["foo"] = "bar"
    request = mock_request("GET", "http://request", headers, body)
    BaseResponse().setup_class(request, request.url, request.headers)


def test_response_metadata() -> None:
    # Setup
    frozen_time = datetime.datetime(
        2023, 5, 20, 10, 20, 30, tzinfo=datetime.timezone.utc
    )
    request = mock_request("GET", "http://request", HTTPHeaders(), None)

    # Execute
    with freeze_time(frozen_time):
        bc = BaseResponse()
        bc.setup_class(request, request.url, request.headers)

    # Verify
    assert "date" in bc.response_headers
    if not settings.TEST_SERVER_MODE:
        assert bc.response_headers["date"] == "Sat, 20 May 2023 10:20:30 GMT"


def test_compression_gzip() -> None:
    body = '{"key": "%D0"}, "C": "#0 = :0"}'
    headers = HTTPHeaders()
    headers["Content-Encoding"] = "gzip"
    request = mock_request(
        "GET",
        url="http://request",
        headers=headers,
        body=_gzip_compress_body(body),
    )
    response = BaseResponse()
    response.setup_class(request, request.url, request.headers)

    assert body == response.body


def test_compression_gzip_in_s3() -> None:
    body = b"some random data"
    headers = HTTPHeaders()
    headers["Content-Encoding"] = "gzip"
    request = mock_request(
        "GET",
        url="http://request",
        headers=headers,
        body=body,
    )
    response = S3Response()
    response.setup_class(request, request.url, request.headers)

    assert body == response.body


def _gzip_compress_body(body: str) -> bytes:
    assert isinstance(body, str)
    return gzip_compress(data=body.encode("utf-8"))
