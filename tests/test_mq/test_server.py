import json
import sure  # noqa # pylint: disable=unused-import

from moto import mock_mq
import moto.server as server
from tests import DEFAULT_ACCOUNT_ID


@mock_mq
def test_mq_list():
    backend = server.create_backend_app(account_id=DEFAULT_ACCOUNT_ID, service="mq")
    test_client = backend.test_client()

    resp = test_client.get("/v1/brokers")
    resp.status_code.should.equal(200)
    json.loads(resp.data).should.equal({"brokerSummaries": []})
