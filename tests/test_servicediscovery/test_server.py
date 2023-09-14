import json

import moto.server as server


def test_servicediscovery_list():
    backend = server.create_backend_app("servicediscovery")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "Route53AutoNaming_v20170314.ListNamespaces"}

    resp = test_client.get("/", headers=headers)
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"Namespaces": []}
