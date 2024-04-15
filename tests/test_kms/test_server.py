import json

import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_list_keys():
    backend = server.create_backend_app("kms")
    test_client = backend.test_client()

    res = test_client.get("/?Action=ListKeys")
    body = json.loads(res.data.decode("utf-8"))

    assert body == {"Keys": [], "NextMarker": None, "Truncated": False}
