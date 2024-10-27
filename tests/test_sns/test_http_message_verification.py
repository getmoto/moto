import base64
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event, Thread
from typing import Optional, Tuple
from unittest import SkipTest
from uuid import uuid4

import boto3
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate

from moto import mock_aws, settings

# Original Request
# https://github.com/getmoto/moto/discussions/7985
# AWS docs
# https://docs.aws.amazon.com/sns/latest/dg/sns-verify-signature-of-message.html
# Request for Boto3 support for this feature
# https://github.com/boto/boto3/issues/2508


class WebRequestHandler(BaseHTTPRequestHandler):
    @property
    def post_data(self):
        content_length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(content_length)

    def do_GET(self):
        msg = json.loads(self.post_data.decode("UTF-8"))
        topic_arn = msg["TopicArn"]
        TestHTTPMessageVerification.MESSAGES_RECEIVED[topic_arn] = msg
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"")

    def do_POST(self):
        self.do_GET()


class ThreadedSnsReceiver:
    def __init__(self):
        self._port = 0

        self._thread: Optional[Thread] = None
        self._ip_address = "0.0.0.0"
        self._server: Optional[HTTPServer] = None
        self._server_ready_event = Event()

    def _server_entry(self) -> None:
        self._server = HTTPServer(("0.0.0.0", 0), WebRequestHandler)
        self._server_ready_event.set()
        self._server.serve_forever()

    def start(self) -> None:
        self._thread = Thread(target=self._server_entry, daemon=True)
        self._thread.start()
        self._server_ready_event.wait()

    def get_host_and_port(self) -> Tuple[str, int]:
        assert self._server is not None, "Make sure to call start() first"
        host, port = self._server.server_address
        return (str(host), port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()

        self._thread.join()  # type: ignore[union-attr]


@mock_aws
class TestHTTPMessageVerification:
    MESSAGES_RECEIVED = {}

    def setup_method(self, *args):
        if not settings.TEST_DECORATOR_MODE:
            raise SkipTest("Can only be tested using decorators")
        self.server = ThreadedSnsReceiver()
        self.server.start()

    def teardown_method(self, *args):
        self.server.stop()

    def test_http_message_verification(self):
        """
        This test verifies that a message sends to a HTTP endpoint contains a valid signature + PEM.
        Steps:

        1. TEST starts a server
        2. TEST creates a topic
        3. TEST creates a HTTP subscription to that topic
        4. TEST publishes a message
        5. MOTO creates a signed message + PEM file
        6. MOTO sends a HTTP request to the server
        7. SERVER receives the message send by Moto containing the signature + link to PEM file
        8. TEST downloads the PEM file from Moto
        9. TEST verifies the signature using the PEM
        """

        conn = boto3.client("sns", region_name="us-east-1")
        topic_arn = conn.create_topic(Name=f"public_{str(uuid4())[0:6]}")["TopicArn"]

        host, port = self.server.get_host_and_port()
        conn.subscribe(
            TopicArn=topic_arn, Protocol="http", Endpoint=f"http://{host}:{port}"
        )

        conn.publish(TopicArn=topic_arn, Message="mymsg", Subject="my汉字subject")

        msg = TestHTTPMessageVerification.MESSAGES_RECEIVED[topic_arn]

        string_to_sign = f"""Message
{msg['Message']}
MessageId
{msg['MessageId']}
Timestamp
{msg['Timestamp']}
TopicArn
{msg['TopicArn']}
Type
{msg['Type']}
"""

        signature = base64.b64decode(msg["Signature"])

        pem = self.download_pem(msg["SigningCertURL"])
        public_key = load_pem_x509_certificate(pem).public_key()

        message_sig_version = msg["SignatureVersion"]
        signature_hash = (
            hashes.SHA1() if message_sig_version == "1" else hashes.SHA256()
        )

        public_key.verify(
            signature,
            string_to_sign.encode(),
            padding=padding.PKCS1v15(),
            algorithm=signature_hash,
        )

    def download_pem(self, url: str) -> bytes:
        return requests.get(url).content
