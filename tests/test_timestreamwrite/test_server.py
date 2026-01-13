import json

import moto.server as server
from moto import mock_aws
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1


@mock_aws
def test_timestreamwrite_list():
    backend = server.create_backend_app("timestream-write")
    test_client = backend.test_client()

    headers = {
        "X-Amz-Target": "Timestream_20181101.ListDatabases",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }
    resp = test_client.post("/", headers=headers, json={})
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"Databases": []}
