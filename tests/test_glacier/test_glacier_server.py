from __future__ import unicode_literals

import json
import sure  # noqa

import moto.server as server
from moto import mock_glacier

"""
Test the different server responses
"""


@mock_glacier
def test_list_vaults():
    backend = server.create_backend_app("glacier")
    test_client = backend.test_client()

    res = test_client.get("/1234bcd/vaults")

    json.loads(res.data.decode("utf-8")).should.equal({"Marker": None, "VaultList": []})
