import datetime
from collections import OrderedDict
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


def test_get_params() -> None:
    subject = BaseResponse()
    subject.querystring = OrderedDict(
        [
            ("Action", ["CreateRule"]),
            ("Version", ["2015-12-01"]),
            (
                "ListenerArn",
                [
                    "arn:aws:elasticloadbalancing:us-east-1:1:listener/my-lb/50dc6c495c0c9188/80139731473870416"
                ],
            ),
            ("Priority", ["100"]),
            ("Conditions.member.1.Field", ["http-header"]),
            ("Conditions.member.1.HttpHeaderConfig.HttpHeaderName", ["User-Agent"]),
            ("Conditions.member.1.HttpHeaderConfig.Values.member.2", ["curl"]),
            ("Conditions.member.1.HttpHeaderConfig.Values.member.1", ["Mozilla"]),
            ("Actions.member.1.FixedResponseConfig.StatusCode", ["200"]),
            ("Actions.member.1.FixedResponseConfig.ContentType", ["text/plain"]),
            ("Actions.member.1.Type", ["fixed-response"]),
        ]
    )

    result = subject._get_params()

    assert result == {
        "Action": "CreateRule",
        "Version": "2015-12-01",
        "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:1:listener/my-lb/50dc6c495c0c9188/80139731473870416",
        "Priority": "100",
        "Conditions": [
            {
                "Field": "http-header",
                "HttpHeaderConfig": {
                    "HttpHeaderName": "User-Agent",
                    "Values": ["Mozilla", "curl"],
                },
            }
        ],
        "Actions": [
            {
                "Type": "fixed-response",
                "FixedResponseConfig": {
                    "StatusCode": "200",
                    "ContentType": "text/plain",
                },
            }
        ],
    }


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
