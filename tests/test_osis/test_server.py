"""Test different server responses."""

import json

import moto.server as server


def test_osis_list():
    backend = server.create_backend_app("osis")
    test_client = backend.test_client()

    resp = test_client.get("/2022-01-01/osis/listPipelines")

    assert resp.status_code == 200
    assert "Pipelines" in json.loads(resp.data)
