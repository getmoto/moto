import json

import moto.server as server
from moto import mock_mediastoredata

"""
Test the different server responses
"""


@mock_mediastoredata
def test_mediastore_lists_containers():
    backend = server.create_backend_app("mediastore-data")
    test_client = backend.test_client()
    body = test_client.get("/").data.decode("utf-8")
    assert json.loads(body) == {"Items": []}
