import json

import moto.server as server
from moto import mock_aws

"""
Test the different server responses
"""


@mock_aws
def test_mediastore_lists_containers():
    backend = server.create_backend_app("mediastore")
    test_client = backend.test_client()

    res = test_client.get(
        "/", headers={"X-Amz-Target": "MediaStore_20170901.ListContainers"}
    )

    result = res.data.decode("utf-8")
    assert json.loads(result) == {"Containers": [], "NextToken": None}
