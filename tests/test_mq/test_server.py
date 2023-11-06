import json

import moto.server as server
from moto import mock_aws


@mock_aws
def test_mq_list():
    backend = server.create_backend_app("mq")
    test_client = backend.test_client()

    resp = test_client.get("/v1/brokers")
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"brokerSummaries": []}
