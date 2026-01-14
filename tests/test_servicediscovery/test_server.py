import json

import moto.server as server
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1


def test_servicediscovery_list():
    backend = server.create_backend_app("servicediscovery")
    test_client = backend.test_client()

    headers = {
        "X-Amz-Target": "Route53AutoNaming_v20170314.ListNamespaces",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
    }

    resp = test_client.post("/", headers=headers)
    assert resp.status_code == 200
    assert json.loads(resp.data) == {"Namespaces": []}
