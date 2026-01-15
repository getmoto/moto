import json

import moto.server as server


def test_es_list():
    backend = server.create_backend_app("es")
    test_client = backend.test_client()
    headers = {"Content-Type": "application/json"}
    resp = test_client.get("/2015-01-01/domain", headers=headers)
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"DomainNames": []}
