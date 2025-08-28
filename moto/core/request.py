from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from werkzeug.wrappers import Request

from moto.core.utils import gzip_decompress

if TYPE_CHECKING:
    from botocore.awsrequest import AWSPreparedRequest


def normalize_request(request: AWSPreparedRequest | Request) -> Request:
    if isinstance(request, Request):
        return request
    body = request.body
    # Request.from_values() does not automatically handle gzip-encoded bodies,
    # like the full WSGI server would, so we need to do it manually.
    if request.headers.get("Content-Encoding") == "gzip":
        body = gzip_decompress(body)  # type: ignore[arg-type]
    parsed_url = urlparse(request.url)
    normalized_request = Request.from_values(
        method=request.method,
        base_url=f"{parsed_url.scheme}://{parsed_url.netloc}",
        path=parsed_url.path,
        query_string=parsed_url.query,
        data=body,
        headers=[(k, v) for k, v in request.headers.items()],
    )
    return normalized_request
