import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from tests import DEFAULT_ACCOUNT_ID


def test_es_list():
    backend = server.create_backend_app(account_id=DEFAULT_ACCOUNT_ID, service="es")
    test_client = backend.test_client()

    resp = test_client.get("/2015-01-01/domain")
    resp.status_code.should.equal(200)
    json.loads(resp.data).should.equals({"DomainNames": []})
