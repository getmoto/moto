"""Tests for the normalized request object.

Regardless of how a request reaches Moto--intercepted from botocore in-process,
served by the Flask app in server mode, or relayed by the proxy--the core code
should see a `moto.core.request.Request`.
"""

import gzip
import json
from io import BytesIO
from typing import Any, cast

import pytest
from botocore.awsrequest import AWSPreparedRequest, HTTPHeaders
from flask import request as flask_request

import moto.server as server
from moto.core.request import Request, normalize_request
from moto.core.responses import BaseResponse

# URLs whose encoding must survive normalization untouched.  The path is the
# interesting part: S3 keys routinely contain characters that werkzeug would
# percent-decode, and moto matches backend URLs against the encoded form.
ROUND_TRIP_URLS = [
    "https://bucket.s3.amazonaws.com/key",
    "https://bucket.s3.amazonaws.com/",
    "https://bucket.s3.amazonaws.com/nested/a/b/c.txt",
    # An object key that itself begins with a slash, via a virtual-hosted URL
    "https://bucket.s3.amazonaws.com//object-key",
    "https://bucket.s3.amazonaws.com//object-key?versionId=1",
    # An encoded slash must not collapse into a path separator
    "https://bucket.s3.amazonaws.com/my%2Fkey",
    "https://bucket.s3.amazonaws.com/my%20key",
    "https://bucket.s3.amazonaws.com/key+with+plus",
    "https://bucket.s3.amazonaws.com/%E2%82%AC-key",
    "https://bucket.s3.amazonaws.com/key?list-type=2&prefix=a%2Fb",
    "https://bucket.s3.amazonaws.com/key?acl",
    "https://sqs.us-east-1.amazonaws.com/123456789012/queue",
    # Custom endpoint with an explicit port
    "http://localhost:5000/bucket/key",
]


def _prepared(
    method: str,
    url: str,
    headers: dict[str, Any] | None = None,
    body: bytes | None = None,
) -> AWSPreparedRequest:
    return AWSPreparedRequest(
        method,
        url,
        cast(HTTPHeaders, headers if headers is not None else {}),
        body,
        stream_output=False,
    )


@pytest.mark.parametrize("url", ROUND_TRIP_URLS)
def test_raw_url_round_trips_through_normalization(url: str) -> None:
    assert normalize_request(_prepared("GET", url)).raw_url == url


@pytest.mark.parametrize("url", ROUND_TRIP_URLS)
def test_raw_url_round_trips_through_the_proxy(url: str) -> None:
    # The proxy builds its request from method/url/headers/body rather than from
    # an intercepted botocore request, but must arrive at the same place.
    assert Request.from_primitives("GET", url, {}, None).raw_url == url


def test_url_without_a_path_is_normalized_to_root() -> None:
    request = normalize_request(_prepared("GET", "https://queue.amazonaws.com"))
    assert request.raw_path == "/"
    assert request.raw_url == "https://queue.amazonaws.com/"


def test_raw_path_keeps_encoding_that_path_discards() -> None:
    request = normalize_request(_prepared("GET", "https://b.s3.amazonaws.com/my%2Fkey"))
    assert request.raw_path == "/my%2Fkey"
    # werkzeug's own `path` decodes, turning one key into two path segments
    assert request.path == "/my/key"


class TestModeParity:
    """The same request, arriving three different ways, should look identical."""

    METHOD = "GET"
    HOST = "localhost:5000"
    # Covers an encoded slash, a leading double slash and a querystring
    PATHS = [
        "/bucket/my%2Fkey?versionId=1",
        "/bucket//object-key",
        "/bucket/my%20key",
        "/bucket/key?acl",
        "/bucket/key",
    ]

    def _in_process(self, path: str) -> Request:
        """What the botocore stubber and the `responses` mock produce."""
        return normalize_request(_prepared(self.METHOD, f"http://{self.HOST}{path}"))

    def _proxy(self, path: str) -> Request:
        """What moto_proxy's MotoRequestHandler produces."""
        return Request.from_primitives(
            self.METHOD, f"http://{self.HOST}{path}", {}, None
        )

    def _server(self, path: str) -> Request:
        """What the Flask app produces, via its configured request_class."""
        captured: list[Request] = []
        app = server.create_backend_app("s3")
        app.before_request(lambda: captured.append(normalize_request(flask_request)))
        app.test_client().open(
            path, method=self.METHOD, headers={"Host": self.HOST, "Authorization": "x"}
        )
        return captured[0]

    @pytest.mark.parametrize("path", PATHS)
    def test_all_modes_agree(self, path: str) -> None:
        requests = {
            "in-process": self._in_process(path),
            "proxy": self._proxy(path),
            "server": self._server(path),
        }

        for mode, request in requests.items():
            assert isinstance(request, Request), mode

        def values_of(attribute: str) -> dict[str, Any]:
            return {mode: getattr(r, attribute) for mode, r in requests.items()}

        assert len(set(values_of("raw_path").values())) == 1, values_of("raw_path")
        assert len(set(values_of("raw_url").values())) == 1, values_of("raw_url")
        assert len(set(values_of("path").values())) == 1, values_of("path")
        assert len(set(values_of("method").values())) == 1, values_of("method")
        assert len(set(values_of("query_string").values())) == 1, values_of(
            "query_string"
        )
        assert {mode: r.get_data() for mode, r in requests.items()} == dict.fromkeys(
            requests, b""
        )

    def test_only_the_server_reports_a_wsgi_origin(self) -> None:
        # moto has to supply its own Date header unless a real WSGI server will.
        assert self._server("/bucket/key").from_wsgi_server is True
        assert self._in_process("/bucket/key").from_wsgi_server is False
        assert self._proxy("/bucket/key").from_wsgi_server is False

    @pytest.mark.parametrize("path", PATHS)
    def test_setup_class_falls_back_to_the_request(self, path: str) -> None:
        # Every entry point now hands the dispatcher request.raw_url, so a
        # response that is given nothing but the request must end up in the same
        # place as one that is handed the url and headers explicitly.
        for request in (self._in_process(path), self._proxy(path), self._server(path)):
            derived, explicit = BaseResponse(), BaseResponse()
            derived.setup_class(request)
            explicit.setup_class(request, request.raw_url, request.headers)

            assert derived.uri == explicit.uri == request.raw_url
            assert derived.path == explicit.path
            assert derived.raw_path == explicit.raw_path == request.raw_path
            assert derived.querystring == explicit.querystring

    def test_date_header_is_supplied_only_when_no_wsgi_server_will(self) -> None:
        def response_for(request: Request) -> BaseResponse:
            response = BaseResponse()
            response.setup_class(request, request.raw_url, request.headers)
            return response

        # werkzeug adds its own Date header in server mode - moto adding a second
        # one used to be prevented by sniffing the request's type name.
        assert "date" not in response_for(self._server("/bucket/key")).response_headers
        assert "date" in response_for(self._in_process("/bucket/key")).response_headers
        assert "date" in response_for(self._proxy("/bucket/key")).response_headers

    def test_server_mode_request_is_not_a_flask_proxy(self) -> None:
        # flask.request is a LocalProxy that unbinds when the request context
        # ends; normalizing has to hand back the object it stands for.
        request = self._server("/bucket/key")
        assert type(request).__name__ == "BackendRequest"
        assert request.raw_path == "/bucket/key"


class TestHeaderNormalization:
    @pytest.mark.parametrize("header", ["Transfer-Encoding", "transfer-encoding"])
    def test_transfer_encoding_is_stripped_whatever_its_casing(
        self, header: str
    ) -> None:
        # The proxy de-chunks the body itself, so the header no longer describes
        # what we are handing on.  Which casing arrives is up to the client.
        request = normalize_request(
            _prepared(
                "PUT",
                "https://b.s3.amazonaws.com/key",
                {header: "chunked"},
                b"hello world",
            )
        )
        assert "Transfer-Encoding" not in request.headers
        assert request.get_data() == b"hello world"

    def test_byte_headers_are_decoded(self) -> None:
        request = normalize_request(
            _prepared("GET", "https://b.s3.amazonaws.com/key", {"x-amz-meta": b"value"})
        )
        assert request.headers["x-amz-meta"] == "value"

    def test_incoming_headers_are_not_mutated(self) -> None:
        prepared = _prepared(
            "GET", "https://b.s3.amazonaws.com/key", {"x-amz-meta": b"value"}
        )
        normalize_request(prepared)
        assert prepared.headers["x-amz-meta"] == b"value"

    def test_content_length_is_restored_for_a_bodiless_request(self) -> None:
        # werkzeug discards `Content-Length: 0`, but S3 answers 411 without it
        request = normalize_request(
            _prepared("PUT", "https://b.s3.amazonaws.com/bucket?acl", {}, b"")
        )
        assert request.headers.get("Content-Length") == "0"

    def test_content_length_reflects_the_body_we_pass_on(self) -> None:
        # aws-chunked bodies advertise the *encoded* length, which no longer
        # applies once the wrapper has been read out
        request = normalize_request(
            _prepared(
                "PUT",
                "https://b.s3.amazonaws.com/key",
                {"Content-Length": "999", "x-amz-decoded-content-length": "11"},
                b"hello world",
            )
        )
        assert request.headers["Content-Length"] == "11"
        assert request.get_data() == b"hello world"

    def test_missing_host_header_is_filled_in(self) -> None:
        # A bare WSGI environ need not carry HTTP_HOST, and request.headers is an
        # immutable view, so the fallback has to go through the environ.
        request = Request(
            {
                "REQUEST_METHOD": "GET",
                "PATH_INFO": "/",
                "SERVER_NAME": "ignored",
                "SERVER_PORT": "80",
                "wsgi.url_scheme": "http",
                "wsgi.input": BytesIO(b""),
            }
        )
        assert "host" not in request.headers

        response = BaseResponse()
        response.setup_class(request, "http://queue.amazonaws.com/", request.headers)

        assert response.headers["host"] == "queue.amazonaws.com"


class TestGzipInServerMode:
    """`decompress_request_body` used to be a Flask before_request handler.

    It now lives on BaseResponse, so it needs coverage through the server, not
    just through a directly-constructed response object.
    """

    def test_gzipped_body_is_decompressed(self) -> None:
        body = json.dumps(
            {
                "TableName": "gzipped",
                "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
                "AttributeDefinitions": [{"AttributeName": "pk", "AttributeType": "S"}],
                "BillingMode": "PAY_PER_REQUEST",
            }
        ).encode()

        response = (
            server.create_backend_app("dynamodb")
            .test_client()
            .post(
                "/",
                data=gzip.compress(body),
                headers={
                    "Host": "dynamodb.us-east-1.amazonaws.com",
                    "Content-Type": "application/x-amz-json-1.0",
                    "X-Amz-Target": "DynamoDB_20120810.CreateTable",
                    "Content-Encoding": "gzip",
                    "Authorization": "AWS4-HMAC-SHA256 Credential=ak/20230101/us-east-1/dynamodb/aws4_request",
                },
            )
        )

        assert response.status_code == 200
        assert json.loads(response.data)["TableDescription"]["TableName"] == "gzipped"

    def test_s3_bodies_are_left_compressed(self) -> None:
        # For S3 the gzip is the object, not a transport encoding
        client = server.create_backend_app("s3").test_client()
        headers = {"Host": "localhost:5000", "Authorization": "x"}
        compressed = gzip.compress(b"some random data")

        client.put("/gzipbucket", headers=headers, content_length=0)
        client.put(
            "/gzipbucket/key.gz",
            data=compressed,
            headers={**headers, "Content-Encoding": "gzip"},
        )
        response = client.get("/gzipbucket/key.gz", headers=headers)

        assert response.data == compressed
