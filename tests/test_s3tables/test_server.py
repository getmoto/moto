"""Test different server responses."""

import string
from random import choice
from urllib.parse import quote

import pytest

import moto.server as server


@pytest.fixture(name="bucket_name")
def table_bucket_name() -> str:
    prefix = "table-bucket"
    random_tag = "".join(choice(string.ascii_letters) for _ in range(10))
    return (prefix + random_tag).lower()


def test_s3tables_list():
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.get("/buckets")

    assert resp.status_code == 200
    assert "tableBuckets" in resp.get_json()


def test_s3tables_create_bucket(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    assert "arn" in resp.get_json()
    assert resp.get_json()["arn"].endswith(bucket_name)


def test_s3tables_get_bucket(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")

    resp = test_client.get(f"/buckets/{quoted_arn}")
    assert resp.status_code == 200


def test_s3tables_delete_bucket(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")

    resp = test_client.delete(f"/buckets/{quoted_arn}")
    assert resp.status_code == 200


def test_s3tables_create_namespace(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")
    resp = test_client.put(f"/namespaces/{quoted_arn}", json={"namespace": ["bar"]})

    assert resp.status_code == 200


def test_s3tables_create_table(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")
    resp = test_client.put(f"/namespaces/{quoted_arn}", json={"namespace": ["bar"]})

    resp = test_client.put(
        f"/tables/{quoted_arn}/bar", json={"name": "baz", "format": "ICEBERG"}
    )
    assert resp.status_code == 200


def test_s3tables_list_tables(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")
    resp = test_client.put(f"/namespaces/{quoted_arn}", json={"namespace": ["bar"]})

    resp = test_client.put(
        f"/tables/{quoted_arn}/bar", json={"name": "baz", "format": "ICEBERG"}
    )

    resp = test_client.get(f"/tables/{quoted_arn}")
    assert resp.get_json()["tables"]


def test_s3tables_get_table(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")
    test_client.put(f"/namespaces/{quoted_arn}", json={"namespace": ["bar"]})

    test_client.put(
        f"/tables/{quoted_arn}/bar", json={"name": "baz", "format": "ICEBERG"}
    )

    resp = test_client.get(f"/get-table?tableBucketARN={arn}&namespace=bar&name=baz")
    assert resp.status_code == 200


def test_s3tables_delete_table(bucket_name: str):
    backend = server.create_backend_app("s3tables")
    test_client = backend.test_client()

    resp = test_client.put("/buckets", json={"name": bucket_name})
    arn = resp.get_json()["arn"]

    quoted_arn = quote(arn, safe="")
    resp = test_client.put(f"/namespaces/{quoted_arn}", json={"namespace": ["bar"]})

    resp = test_client.put(
        f"/tables/{quoted_arn}/bar", json={"name": "baz", "format": "ICEBERG"}
    )

    resp = test_client.delete(f"/tables/{quoted_arn}/bar/baz")
    assert resp.status_code == 200
