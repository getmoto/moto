import json

import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_list_vaults():
    backend = server.create_backend_app("glacier")
    test_client = backend.test_client()

    res = test_client.get("/1234bcd/vaults")

    assert json.loads(res.data.decode("utf-8")) == {"Marker": None, "VaultList": []}
