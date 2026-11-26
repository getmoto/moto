"""Mocking the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

import asyncio
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Any

import pytest

from moto import mock_aws

try:
    from aws_sdk_sqs import AsyncSQSClient, AsyncSQSConfig, SQSClient, SQSConfig
    from smithy_http.aio.aiohttp import AIOHTTPClient
    from smithy_http.urllib3 import Urllib3HTTPClient
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-sqs is not installed", allow_module_level=True)


def test_http_clients_are_only_patched_while_mocking() -> None:
    sync_send, async_send = Urllib3HTTPClient.send, AIOHTTPClient.send

    with mock_aws():
        with mock_aws():
            assert Urllib3HTTPClient.send is not sync_send
            assert AIOHTTPClient.send is not async_send
        # Still mocked, as long as the outer mock is active
        assert Urllib3HTTPClient.send is not sync_send
        assert AIOHTTPClient.send is not async_send

    assert Urllib3HTTPClient.send is sync_send
    assert AIOHTTPClient.send is async_send


@mock_aws
def test_async_client() -> None:
    async def send_and_receive() -> list[str | None]:
        config = await AsyncSQSConfig.resolve(region="eu-west-1")
        async with AsyncSQSClient(config=config) as client:
            queue_url = (
                await client.create_queue(queue_name="notifications")
            ).queue_url
            assert queue_url
            await client.send_message(queue_url=queue_url, message_body="hi")
            received = await client.receive_message(queue_url=queue_url)
            return [message.body for message in received.messages or []]

    assert asyncio.run(send_and_receive()) == ["hi"]


class SQSCompatibleHandler(BaseHTTPRequestHandler):
    """A non-AWS endpoint that implements the CreateQueue-operation"""

    request_bodies: list[bytes] = []

    def do_POST(self) -> None:
        content_length = int(self.headers["Content-Length"])
        self.request_bodies.append(self.rfile.read(content_length))
        body = json.dumps({"QueueUrl": "http://sqs.example.com/queue"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/x-amz-json-1.0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: Any) -> None:
        pass


def test_requests_to_other_endpoints_are_sent_as_usual() -> None:
    server = HTTPServer(("127.0.0.1", 0), SQSCompatibleHandler)
    Thread(target=server.serve_forever, daemon=True).start()
    endpoint = f"http://127.0.0.1:{server.server_address[1]}"
    SQSCompatibleHandler.request_bodies.clear()

    async def create_queue_async() -> str | None:
        config = await AsyncSQSConfig.resolve(region="eu-west-1", endpoint_uri=endpoint)
        async with AsyncSQSClient(config=config) as client:
            return (await client.create_queue(queue_name="async-queue")).queue_url

    try:
        with mock_aws():
            config = SQSConfig.resolve(region="eu-west-1", endpoint_uri=endpoint)
            with SQSClient(config=config) as client:
                queue_url = client.create_queue(queue_name="sync-queue").queue_url
            async_queue_url = asyncio.run(create_queue_async())
    finally:
        server.shutdown()

    assert queue_url == "http://sqs.example.com/queue"
    assert async_queue_url == "http://sqs.example.com/queue"
    assert [json.loads(body) for body in SQSCompatibleHandler.request_bodies] == [
        {"QueueName": "sync-queue"},
        {"QueueName": "async-queue"},
    ]
