import os
from typing import Dict, Optional
from unittest import SkipTest

import requests
import xmltodict

from moto import settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.server import ThreadedMotoServer

SERVER_PORT = 5001
BASE_URL = f"http://localhost:{SERVER_PORT}/"


class TestAccountIdResolution:
    def setup_method(self) -> None:
        if settings.TEST_SERVER_MODE:
            raise SkipTest(
                "No point in testing this in ServerMode, as we already start our own server"
            )
        self.server = ThreadedMotoServer(port=SERVER_PORT, verbose=False)
        self.server.start()

    def teardown_method(self) -> None:
        self.server.stop()

    def test_environment_variable_takes_precedence(self) -> None:
        # Verify ACCOUNT ID is standard
        resp = self._get_caller_identity()
        assert self._get_account_id(resp) == ACCOUNT_ID

        # Specify environment variable, and verify this becomes the new ACCOUNT ID
        os.environ["MOTO_ACCOUNT_ID"] = "111122223333"
        resp = self._get_caller_identity()
        assert self._get_account_id(resp) == "111122223333"

        # Specify special request header - the environment variable should still take precedence
        resp = self._get_caller_identity(
            extra_headers={"x-moto-account-id": "333344445555"}
        )
        assert self._get_account_id(resp) == "111122223333"

        # Remove the environment variable - the Request Header should now take precedence
        del os.environ["MOTO_ACCOUNT_ID"]
        resp = self._get_caller_identity(
            extra_headers={"x-moto-account-id": "333344445555"}
        )
        assert self._get_account_id(resp) == "333344445555"

        # Without Header, we're back to the regular account ID
        resp = self._get_caller_identity()
        assert self._get_account_id(resp) == ACCOUNT_ID

    def _get_caller_identity(
        self, extra_headers: Optional[Dict[str, str]] = None
    ) -> requests.Response:
        data = "Action=GetCallerIdentity&Version=2011-06-15"
        headers = {
            "Authorization": "AWS4-HMAC-SHA256 Credential=abcd/20010101/us-east-2/sts/aws4_request, SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature=...",
            "Content-Length": f"{len(data)}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        headers.update(extra_headers or {})
        return requests.post(f"{BASE_URL}", headers=headers, data=data)

    def _get_account_id(self, resp: requests.Response) -> str:
        data = xmltodict.parse(resp.content)
        return data["GetCallerIdentityResponse"]["GetCallerIdentityResult"]["Account"]
