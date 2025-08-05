from __future__ import annotations

from urllib.parse import urlparse

from botocore.awsrequest import AWSPreparedRequest
from werkzeug.wrappers import Request


def normalize_request(request: AWSPreparedRequest | Request) -> Request:
    if isinstance(request, Request):
        return request
    parsed_url = urlparse(request.url)
    normalized_request = Request.from_values(
        method=request.method,
        base_url=f"{parsed_url.scheme}://{parsed_url.netloc}",
        path=parsed_url.path,
        query_string=parsed_url.query,
        data=request.body,
        headers=[(k, v) for k, v in request.headers.items()],
    )
    return normalized_request
