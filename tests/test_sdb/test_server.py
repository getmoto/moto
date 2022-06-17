"""Test different server responses."""
import sure  # noqa # pylint: disable=unused-import

import moto.server as server
from moto import mock_sdb
from tests import DEFAULT_ACCOUNT_ID


@mock_sdb
def test_sdb_list():
    backend = server.create_backend_app(account_id=DEFAULT_ACCOUNT_ID, service="sdb")
    test_client = backend.test_client()

    resp = test_client.post("/", data={"Action": "ListDomains"})
    resp.status_code.should.equal(200)
    str(resp.data).should.contain("ListDomainsResult")
