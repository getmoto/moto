from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

from botocore.httpchecksum import AwsChunkedWrapper
from werkzeug.local import LocalProxy
from werkzeug.wrappers import Request as WerkzeugRequest

from moto.settings import MAX_FORM_MEMORY_SIZE
from moto.utilities.constants import APPLICATION_JSON, JSON_TYPES

if TYPE_CHECKING:
    from botocore.awsrequest import AWSPreparedRequest
    from requests import PreparedRequest

    from moto.core.model import ServiceModel


class Request(WerkzeugRequest):
    #: True when this request was received by a real WSGI server (Moto Server).
    from_wsgi_server = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.max_form_memory_size = MAX_FORM_MEMORY_SIZE

    @classmethod
    def from_primitives(
        cls, method: str, url: str, headers: Any, body: Any = None
    ) -> Request:
        """Build a request from the basic components of an HTTP message."""
        if isinstance(body, AwsChunkedWrapper):
            body = body.read()
        parsed_url = urlparse(url)
        request = cast(
            Request,
            cls.from_values(
                method=method,
                base_url=f"{parsed_url.scheme}://{parsed_url.netloc}",
                path=parsed_url.path,
                query_string=parsed_url.query,
                data=body if body is not None else b"",
                # The proxy de-chunks before we ever see the request, and we (above) read
                # an AwsChunkedWrapper out in full, so Transfer-Encoding no longer applies.
                headers=[
                    (key, value.decode("utf-8") if isinstance(value, bytes) else value)
                    for key, value in headers.items()
                    if key.lower() not in ["transfer-encoding"]
                ],
            ),
        )
        # Ensure a Content-Length header is present, even for bodiless requests.
        # (Some S3 endpoints return a 411 if this header is missing.)
        request.environ.setdefault("CONTENT_LENGTH", "0")
        return request

    @property
    def raw_path(self) -> str:
        """The path as it arrived, before werkzeug percent-decoded it.

        S3 keys routinely contain characters - an encoded slash, most awkwardly -
        that `path` decodes away, and Moto matches backend URLs against the
        encoded form.
        """
        # RAW_URI holds either a path or a full URL, depending on the server.
        # A path may begin with a double slash, which urlparse would read as the
        # start of a netloc, so only parse when there is really a scheme to strip.
        raw_uri: str = self.environ.get("RAW_URI", "") or self.path
        parsed = urlparse(raw_uri)
        raw_path = parsed.path if parsed.scheme else raw_uri.split("?", 1)[0]
        if not raw_path:
            return "/"
        return raw_path if raw_path.startswith("/") else f"/{raw_path}"

    @property
    def raw_url(self) -> str:
        """The full URL as it arrived.  See `raw_path`."""
        raw_url = f"{self.url_root.rstrip('/')}{self.raw_path}"
        if self.query_string:
            raw_url += f"?{self.query_string.decode()}"
        return raw_url


def normalize_request(
    request: AWSPreparedRequest
    | LocalProxy[WerkzeugRequest]
    | PreparedRequest
    | Request
    | WerkzeugRequest,
) -> Request:
    """Turn however this request reached us into the one type the core acts on."""
    if isinstance(request, LocalProxy):
        request = request._get_current_object()
    if isinstance(request, Request):
        return request
    if isinstance(request, WerkzeugRequest):
        return Request(request.environ.copy())
    # Anything else is a prepared request from Botocore or Requests (via Responses).
    assert request.method and request.url
    return Request.from_primitives(
        request.method, request.url, request.headers, request.body
    )


def determine_request_protocol(
    service_model: ServiceModel, content_type: str | None = None
) -> str:
    protocol = str(service_model.protocol)
    # Short circuit protocol detection for S3 because the ContentType header
    # is often set based on the MIME type of the object data being uploaded.
    if service_model.service_name == "s3":
        return protocol
    supported_protocols = service_model.metadata.get("protocols", [protocol])
    content_type = content_type if content_type is not None else ""
    if content_type in JSON_TYPES:
        protocol = "rest-json" if content_type == APPLICATION_JSON else "json"
    elif content_type.startswith("application/x-www-form-urlencoded"):
        protocol = "ec2" if "ec2" in supported_protocols else "query"
    if protocol not in supported_protocols:
        raise NotImplementedError(
            f"Unsupported protocol [{protocol}] for service {service_model.service_name}"
        )
    return protocol
