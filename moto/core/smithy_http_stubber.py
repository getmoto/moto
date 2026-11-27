"""
Mocks the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python

This SDK does not use botocore, so the BotocoreStubber never sees its requests.
Its clients send requests using the HTTP clients from `smithy-http` instead:
 - `Urllib3HTTPClient` for synchronous clients
 - `AIOHTTPClient` for asynchronous clients

While Moto is active, the `send`-method of these HTTP clients is patched, and requests are processed by Moto.
Requests that Moto does not intercept (passthrough URLs, non-AWS URLs) are still sent using the original HTTP client.

An alternative would be to start a ThreadedMotoServer, and point the SDK to it using the
`AWS_ENDPOINT_URL`/`AWS_ENDPOINT_URL_<SERVICE>` environment variables, which this SDK supports.
Botocore reads the same environment variables though, so we would also have to set `AWS_IGNORE_CONFIGURED_ENDPOINT_URLS`
to keep boto3-requests in-process. That only works for as long as the AWS SDK for Python v4 does not support that variable.
Once it does, its requests would be sent to AWS instead of Moto.
"""

import copy
import dataclasses
from collections.abc import Callable
from http.client import responses as http_reasons
from io import BytesIO
from typing import Any
from unittest.mock import patch
from urllib.parse import urlparse

from botocore.awsrequest import AWSPreparedRequest
from botocore.compat import HTTPHeaders

from moto.core.common_types import TYPE_RESPONSE


class SmithyHTTPStubber:
    def __init__(self, process_request: Callable[[AWSPreparedRequest], Any]):
        """
        :param process_request: Processes a request in-process, and returns either a response-tuple (status, headers, body), or None if the request should not be intercepted
        """
        self._process_request = process_request
        self._patchers: list[Any] = []

    def start(self, endpoint: str | None = None) -> None:
        """
        Patch the HTTP clients of the AWS SDK for Python v4, if it is installed.

        :param endpoint: Send requests for AWS to the MotoServer/MotoProxy that runs on this endpoint, instead of processing them in-process.
        """
        for http_client, fake_send in self._fake_send_methods(endpoint):
            patcher = patch.object(http_client, "send", fake_send)
            patcher.start()
            self._patchers.append(patcher)

    def stop(self) -> None:
        for patcher in self._patchers:
            patcher.stop()
        self._patchers.clear()

    def _fake_send_methods(self, endpoint: str | None) -> list[tuple[type, Any]]:
        sync_client, async_client = _installed_http_clients()
        fake_send_methods: list[tuple[type, Any]] = []
        if sync_client is not None:
            fake_send = self._fake_sync_send(sync_client.send, endpoint)
            fake_send_methods.append((sync_client, fake_send))
        if async_client is not None:
            fake_send = self._fake_async_send(async_client.send, endpoint)
            fake_send_methods.append((async_client, fake_send))
        return fake_send_methods

    def _fake_sync_send(self, original_send: Any, endpoint: str | None) -> Any:
        from smithy_http import HTTPResponse

        def send(http_client: Any, request: Any, *, request_config: Any = None) -> Any:
            if endpoint:
                if _is_aws_request(request):
                    request = _redirect(request, endpoint)
                return original_send(
                    http_client, request, request_config=request_config
                )
            body = request.consume_body()
            response = self._process_request(_to_botocore_request(request, body))
            if response is None:
                # The body has been consumed, so we have to pass it on explicitly
                request = dataclasses.replace(request, body=body)
                return original_send(
                    http_client, request, request_config=request_config
                )
            status, fields, response_body = _from_moto_response(response)
            return HTTPResponse(
                status=status,
                fields=fields,
                body=BytesIO(response_body),
                reason=http_reasons.get(status),
            )

        return send

    def _fake_async_send(self, original_send: Any, endpoint: str | None) -> Any:
        from smithy_core.aio.utils import list_async, read_streaming_blob_async
        from smithy_http import HTTPResponse

        async def send(
            http_client: Any, request: Any, *, request_config: Any = None
        ) -> Any:
            if endpoint:
                if _is_aws_request(request):
                    request = _redirect(request, endpoint)
                return await original_send(
                    http_client, request, request_config=request_config
                )
            body = await read_streaming_blob_async(request.body)
            response = self._process_request(_to_botocore_request(request, body))
            if response is None:
                # The body has been consumed, so we have to pass it on explicitly
                request = dataclasses.replace(request, body=body)
                return await original_send(
                    http_client, request, request_config=request_config
                )
            status, fields, response_body = _from_moto_response(response)
            return HTTPResponse(
                status=status,
                fields=fields,
                body=list_async([response_body]),
                reason=http_reasons.get(status),
            )

        return send


_http_clients: tuple[Any, Any] | None = None


def _installed_http_clients() -> tuple[Any, Any]:
    """
    The (sync, async) HTTP clients of the AWS SDK for Python v4, if it is installed.
    Only looked up once, as failed imports are not cached by Python.
    """
    global _http_clients
    if _http_clients is None:
        sync_client: Any = None
        async_client: Any = None
        try:
            from smithy_http.urllib3 import Urllib3HTTPClient

            sync_client = Urllib3HTTPClient
        except ImportError:
            pass
        try:
            from smithy_http.aio.aiohttp import AIOHTTPClient

            async_client = AIOHTTPClient
        except ImportError:
            pass
        _http_clients = (sync_client, async_client)
    return _http_clients


def _to_botocore_request(request: Any, body: bytes) -> AWSPreparedRequest:
    headers = HTTPHeaders()
    for field in request.fields.get_by_type("header"):
        for name, value in field.as_tuples():
            headers[name] = value
    return AWSPreparedRequest(
        method=request.method,
        url=request.destination.build(),
        headers=headers,
        body=body,
        stream_output=False,
    )


def _from_moto_response(response: TYPE_RESPONSE) -> tuple[int, Any, bytes]:
    from smithy_http import tuples_to_fields

    status, headers, body = response
    fields = tuples_to_fields(
        (name, value.decode("utf-8") if isinstance(value, bytes) else str(value))
        for name, value in headers.items()
        if value is not None
    )
    if isinstance(body, str):
        body = body.encode("utf-8")
    return int(status), fields, body or b""


def _is_aws_request(request: Any) -> bool:
    """Whether Moto would intercept this request, if it was processed in-process"""
    from moto.backend_index import backend_url_patterns
    from moto.core.utils import get_equivalent_url_in_aws_domain

    parsed_url, _ = get_equivalent_url_in_aws_domain(request.destination.build())
    clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    return any(pattern.match(clean_url) for _, pattern in backend_url_patterns)


def _redirect(request: Any, endpoint: str) -> Any:
    """
    Send the request to a MotoServer/MotoProxy instead.
    The Host-header stays the same, so that Moto knows which service/region the request is for.
    """
    from smithy_http import Field

    destination = request.destination
    host = destination.host
    if destination.port is not None:
        host = f"{host}:{destination.port}"
    fields = copy.deepcopy(request.fields)
    fields.set_field(Field(name="Host", values=[host]))

    server = urlparse(endpoint)
    return dataclasses.replace(
        request,
        destination=dataclasses.replace(
            destination,
            scheme=server.scheme,
            host=server.hostname,
            port=server.port,
        ),
        fields=fields,
    )
