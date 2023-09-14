"""Test the different server responses."""
import json
import moto.server as server


def test_list_virtual_clusters():
    backend = server.create_backend_app("emr-containers")
    test_client = backend.test_client()

    res = test_client.get("/virtualclusters")

    assert "virtualClusters" in json.loads(res.data)
