import json

from moto import mock_mq
import moto.server as server


@mock_mq
def test_mq_list():
    backend = server.create_backend_app("mq")
    test_client = backend.test_client()

    resp = test_client.get("/v1/brokers")
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"brokerSummaries": []}
