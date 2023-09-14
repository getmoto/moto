import json
import moto.server as server
from moto import mock_medialive

"""
Test the different server responses
"""


@mock_medialive
def test_medialive_list_channels():
    backend = server.create_backend_app("medialive")
    test_client = backend.test_client()

    res = test_client.get("/prod/channels")
    result = res.data.decode("utf-8")
    assert json.loads(result) == {"channels": [], "nextToken": None}


@mock_medialive
def test_medialive_list_inputs():
    backend = server.create_backend_app("medialive")
    test_client = backend.test_client()

    res = test_client.get("/prod/inputs")

    result = res.data.decode("utf-8")
    assert json.loads(result) == {"inputs": [], "nextToken": None}
