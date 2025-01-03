"""Test different server responses."""

import moto.server as server


def test_s3tables_list():
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.get("/buckets")

    assert resp.status_code == 200
    assert "tableBuckets" in resp.get_json()

def test_s3tables_create_bucket():
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": "foo"})
    assert "arn" in resp.get_json()
    assert resp.get_json()["arn"].endswith("foo")

