import json

import moto.server as server


def test_dax_list():
    backend = server.create_backend_app("dax")
    test_client = backend.test_client()
    resp = test_client.post(
        "/", headers={"X-Amz-Target": "AmazonDAXV3.DescribeClusters"}, data="{}"
    )

    assert resp.status_code == 200
    assert json.loads(resp.data) == {"Clusters": [], "NextToken": None}
