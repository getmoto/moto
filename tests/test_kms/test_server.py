import json

import moto.server as server
from moto import mock_aws
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1

"""
Test the different server responses
"""


@mock_aws
def test_list_keys():
    backend = server.create_backend_app("kms")
    test_client = backend.test_client()
    headers = {
        "X-Amz-Target": "TrentService.ListKeys",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    res = test_client.post("/", headers=headers)
    body = json.loads(res.data.decode("utf-8"))

    assert body == {"Keys": [], "NextMarker": None, "Truncated": False}
