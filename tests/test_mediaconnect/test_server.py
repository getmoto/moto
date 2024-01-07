import json

import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_mediaconnect_list_flows():
    backend = server.create_backend_app("mediaconnect")
    test_client = backend.test_client()

    res = test_client.get("/v1/flows")

    result = res.data.decode("utf-8")
    assert json.loads(result) == {"flows": []}
