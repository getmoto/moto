import json

import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_mediastore_lists_containers():
    backend = server.create_backend_app("mediastore-data")
    test_client = backend.test_client()
    body = test_client.get("/").data.decode("utf-8")
    assert json.loads(body) == {"Items": []}
