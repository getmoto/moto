"""Test different server responses."""

import moto.server as server


def test_docdbelastic_list():
    backend = server.create_backend_app("docdb-elastic")
    test_client = backend.test_client()

    resp = test_client.get("/clusters")

    assert resp.status_code == 200
    assert resp.json == {"clusters": []}
