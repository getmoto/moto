"""
Ensure that the responses module plays nice with our mocks
"""

from http.server import BaseHTTPRequestHandler
from unittest import SkipTest, TestCase

import boto3
import requests
import responses

from moto import mock_aws, settings
from moto.core.models import override_responses_real_send
from moto.core.versions import RESPONSES_VERSION
from moto.utilities.distutils_version import LooseVersion

from .utilities import SimpleServer


class TestResponsesModule(TestCase):
    def setUp(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest("No point in testing responses-decorator in ServerMode")

    @mock_aws
    @responses.activate
    def test_moto_first(self) -> None:  # type: ignore[misc]
        """
        Verify we can activate a user-defined `responses` on top of our Moto mocks
        """
        self.moto_responses_compatibility()

    @responses.activate
    @mock_aws
    def test_moto_second(self) -> None:
        """
        Verify we can load Moto after activating a `responses`-mock
        """
        self.moto_responses_compatibility()

    def moto_responses_compatibility(self) -> None:
        responses.add(
            responses.GET, url="http://127.0.0.1/lkdsfjlkdsa", json={"a": "4"}
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="mybucket")
        s3.put_object(Bucket="mybucket", Key="name", Body="value")
        s3.get_object(Bucket="mybucket", Key="name")["Body"].read()
        with requests.get("http://127.0.0.1/lkdsfjlkdsa") as r:
            assert r.json() == {"a": "4"}

    @responses.activate
    def test_moto_as_late_as_possible(self) -> None:
        """
        Verify we can load moto after registering a response
        """
        responses.add(
            responses.GET, url="http://127.0.0.1/lkdsfjlkdsa", json={"a": "4"}
        )
        with mock_aws():
            s3 = boto3.client("s3", region_name="us-east-1")
            s3.create_bucket(Bucket="mybucket")
            s3.put_object(Bucket="mybucket", Key="name", Body="value")
            # This mock exists within Moto
            with requests.get("http://127.0.0.1/lkdsfjlkdsa") as r:
                assert r.json() == {"a": "4"}

        # And outside of Moto
        with requests.get("http://127.0.0.1/lkdsfjlkdsa") as r:
            assert r.json() == {"a": "4"}


class WebRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"real response")


@mock_aws
class TestResponsesMockWithPassThru(TestCase):
    """
    https://github.com/getmoto/moto/issues/6417
    """

    def setUp(self) -> None:
        if RESPONSES_VERSION < LooseVersion("0.24.0"):
            raise SkipTest("Can only test this with responses >= 0.24.0")

        self.server = SimpleServer(WebRequestHandler)
        self.server.start()
        host, port = self.server.get_host_and_port()
        self.server_url = f"http://{host}:{port}"

        self.r_mock = responses.RequestsMock(assert_all_requests_are_fired=True)
        override_responses_real_send(self.r_mock)
        self.r_mock.start()
        self.r_mock.add_passthru(self.server_url)

    def tearDown(self) -> None:
        self.r_mock.stop()  # type: ignore
        self.r_mock.reset()  # type: ignore
        override_responses_real_send(None)

        self.server.stop()

    def http_requests(self) -> str:
        # Mock this website
        requests.post("https://example.org")

        # Passthrough this website
        assert requests.get(self.server_url).content == b"real response"

        return "OK"

    def aws_and_http_requests(self) -> str:
        ddb = boto3.client("dynamodb", "us-east-1")
        assert ddb.list_tables()["TableNames"] == []
        self.http_requests()
        return "OK"

    def test_http_requests(self) -> None:
        self.r_mock.add(responses.POST, "https://example.org", status=200)  # type: ignore
        self.assertEqual("OK", self.http_requests())

    def test_aws_and_http_requests(self) -> None:
        self.r_mock.add(responses.POST, "https://example.org", status=200)  # type: ignore
        self.assertEqual("OK", self.aws_and_http_requests())
