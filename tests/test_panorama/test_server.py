"""Test different server responses."""

import moto.server as server


def test_panorama_list():
    backend = server.create_backend_app("panorama")
    test_client = backend.test_client()

    resp = test_client.get("/devices")

    assert resp.status_code == 200
