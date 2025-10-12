"""Test different server responses."""

import moto.server as server


def test_emrserverless_list():
    backend = server.create_backend_app("emr-serverless")
    test_client = backend.test_client()

    resp = test_client.get("/applications")
    assert resp.status_code == 200
    assert "applications" in str(resp.data)
