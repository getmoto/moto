from unittest import SkipTest

import requests

from moto import settings
from moto.server import ThreadedMotoServer


SERVER_PORT = 5001
BASE_URL = f"http://localhost:{SERVER_PORT}/"


class TestAccountIdResolution:
    def setup_method(self):
        if not settings.TEST_DECORATOR_MODE:
            raise SkipTest(
                "No point in testing this in ServerMode, as we already start our own server"
            )
        self.server = ThreadedMotoServer(port=SERVER_PORT, verbose=False)
        self.server.start()

    def teardown_method(self):
        self.server.stop()

    def test_with_custom_request_header(self):
        buckets_for_account_1 = ["foo", "bar"]
        for name in buckets_for_account_1:
            requests.put(f"http://{name}.localhost:{SERVER_PORT}/")

        res = requests.get(BASE_URL)
        assert b"<Name>foo</Name>" in res.content
        assert b"<Name>bar</Name>" in res.content

        # Create two more buckets in another account
        headers = {"x-moto-account-id": "333344445555"}
        buckets_for_account_2 = ["baz", "bla"]
        for name in buckets_for_account_2:
            requests.put(f"http://{name}.localhost:{SERVER_PORT}/", headers=headers)

        # Verify only these buckets exist in this account
        res = requests.get(BASE_URL, headers=headers)
        assert b"<Name>baz</Name>" in res.content
        assert b"<Name>bla</Name>" in res.content
        assert b"<Name>foo</Name>" not in res.content
        assert b"<Name>bar</Name>" not in res.content

        # Verify these buckets do not exist in the original account
        res = requests.get(BASE_URL)
        assert b"<Name>baz</Name>" not in res.content
        assert b"<Name>bla</Name>" not in res.content
