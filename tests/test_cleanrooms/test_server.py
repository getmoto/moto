"""Test different server responses."""

import json

import moto.server as server


def test_cleanrooms_list_collaborations():
    backend = server.create_backend_app("cleanrooms")
    test_client = backend.test_client()

    resp = test_client.get("/collaborations")

    assert resp.status_code == 200
    assert "collaborationList" in json.loads(resp.data)
