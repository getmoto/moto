import json
import sure  # noqa # pylint: disable=unused-import

import moto.server as server


def test_servicediscovery_list():
    backend = server.create_backend_app("servicediscovery")
    test_client = backend.test_client()

    headers = {"X-Amz-Target": "Route53AutoNaming_v20170314.ListNamespaces"}

    resp = test_client.get("/", headers=headers)
    resp.status_code.should.equal(200)
    json.loads(resp.data).should.equal({"Namespaces": []})
