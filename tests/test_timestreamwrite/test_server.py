import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_timestreamwrite
from tests import DEFAULT_ACCOUNT_ID


@mock_timestreamwrite
def test_timestreamwrite_list():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="timestream-write"
    )
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "Timestream_20181101.ListDatabases"}
    resp = test_client.post("/", headers=headers, json={})
    resp.status_code.should.equal(200)
    json.loads(resp.data).should.equal({"Databases": []})
