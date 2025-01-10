"""Test different server responses."""

from urllib.parse import quote

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


def test_s3tables_get_bucket():
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": "foo"})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")

    resp = test_client.get(f"/buckets/{quoted_arn}")
    assert resp.status_code == 200

def test_s3tables_delete_bucket():
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": "foo"})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")

    resp = test_client.delete(f"/buckets/{quoted_arn}")
    assert resp.status_code == 200
