import requests

from moto import settings
from moto.server import ThreadedMotoServer
from unittest import SkipTest


SERVER_PORT = 5001
BASE_URL = f"http://localhost:{SERVER_PORT}/"


class TestAccountIdResolution:
    def setup(self):
        if settings.TEST_SERVER_MODE:
            raise SkipTest(
                "No point in testing this in ServerMode, as we already start our own server"
            )
        self.server = ThreadedMotoServer(port=SERVER_PORT, verbose=False)
        self.server.start()

    def teardown(self):
        self.server.stop()

    def test_with_custom_request_header(self):
        buckets_for_account_1 = ["foo", "bar"]
        for name in buckets_for_account_1:
            requests.put(f"http://{name}.localhost:{SERVER_PORT}/")

        res = requests.get(BASE_URL)
        res.content.should.contain(b"<Name>foo</Name>")
        res.content.should.contain(b"<Name>bar</Name>")

        # Create two more buckets in another account
        headers = {"x-moto-account-id": "333344445555"}
        buckets_for_account_2 = ["baz", "bla"]
        for name in buckets_for_account_2:
            requests.put(f"http://{name}.localhost:{SERVER_PORT}/", headers=headers)

        # Verify only these buckets exist in this account
        res = requests.get(BASE_URL, headers=headers)
        res.content.should.contain(b"<Name>baz</Name>")
        res.content.should.contain(b"<Name>bla</Name>")
        res.content.shouldnt.contain(b"<Name>foo</Name>")
        res.content.shouldnt.contain(b"<Name>bar</Name>")

        # Verify these buckets do not exist in the original account
        res = requests.get(BASE_URL)
        res.content.shouldnt.contain(b"<Name>baz</Name>")
        res.content.shouldnt.contain(b"<Name>bla</Name>")
