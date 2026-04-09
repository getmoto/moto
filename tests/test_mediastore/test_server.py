import json

import moto.server as server
from moto import mock_aws
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1

"""
Test the different server responses
"""


@mock_aws
def test_mediastore_lists_containers():
    backend = server.create_backend_app("mediastore")
    test_client = backend.test_client()

    res = test_client.post(
        "/",
        headers={
            "X-Amz-Target": "MediaStore_20170901.ListContainers",
            "Content-Type": APPLICATION_AMZ_JSON_1_1,
        },
    )

    result = res.data.decode("utf-8")
    assert json.loads(result) == {"Containers": [], "NextToken": None}
