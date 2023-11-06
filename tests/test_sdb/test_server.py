import moto.server as server
from moto import mock_aws


@mock_aws
def test_sdb_list():
    backend = server.create_backend_app("sdb")
    test_client = backend.test_client()

    resp = test_client.post("/", data={"Action": "ListDomains"})
    assert resp.status_code == 200
    assert "ListDomainsResult" in str(resp.data)
