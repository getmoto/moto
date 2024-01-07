import json

import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_mediapackage_list_channels():
    backend = server.create_backend_app("mediapackage")
    test_client = backend.test_client()

    res = test_client.get("/channels")
    result = res.data.decode("utf-8")
    assert json.loads(result) == {"channels": []}


@mock_aws
def test_mediapackage_list_origin_endpoints():
    backend = server.create_backend_app("mediapackage")
    test_client = backend.test_client()

    res = test_client.get("/origin_endpoints")
    result = res.data.decode("utf-8")
    assert json.loads(result) == {"originEndpoints": []}
