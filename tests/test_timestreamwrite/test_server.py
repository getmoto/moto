import json

import moto.server as server
from moto import mock_timestreamwrite


@mock_timestreamwrite
def test_timestreamwrite_list():
    backend = server.create_backend_app("timestream-write")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "Timestream_20181101.ListDatabases"}
    resp = test_client.post("/", headers=headers, json={})
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"Databases": []}
