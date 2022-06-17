"""Test different server responses."""
import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_cloudtrail
from tests import DEFAULT_ACCOUNT_ID


@mock_cloudtrail
def test_cloudtrail_list():
    backend = server.create_backend_app(
        account_id=DEFAULT_ACCOUNT_ID, service="cloudtrail"
    )
    test_client = backend.test_client()

    headers = {
        "X-Amz-Target": "com.amazonaws.cloudtrail.v20131101.CloudTrail_20131101.ListTrails"
    }
    res = test_client.post("/", headers=headers)
    data = json.loads(res.data)
    data.should.equal({"Trails": []})
