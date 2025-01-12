"""Unit tests for s3tables-supported APIs."""

import boto3
import pytest

from moto import mock_aws


@mock_aws
def test_create_table_bucket():
    client = boto3.client("s3tables", region_name="us-east-1")
    response = client.create_table_bucket(name="foo")
    assert "arn" in response
    assert response["arn"].endswith("foo")


@mock_aws
def test_create_table_bucket_validates_name():
    client = boto3.client("s3tables", region_name="us-east-1")
    with pytest.raises(client.exceptions.BadRequestException) as exc:
        client.create_table_bucket(name="sthree-invalid-name")
    assert exc.match("bucket name is not valid")


@mock_aws
def test_list_table_buckets():
    client = boto3.client("s3tables", region_name="us-east-2")
    client.create_table_bucket(name="foo")
    response = client.list_table_buckets(prefix="foo")
    assert "tableBuckets" in response
    assert len(response["tableBuckets"]) == 1
    assert response["tableBuckets"][0]["name"] == "foo"


@mock_aws
def test_list_table_buckets_pagination():
    client = boto3.client("s3tables", region_name="us-east-2")
    client.create_table_bucket(name="foo")
    client.create_table_bucket(name="bar")
    response = client.list_table_buckets(maxBuckets=1)

    assert len(response["tableBuckets"]) == 1
    assert "continuationToken" in response

    response = client.list_table_buckets(
        maxBuckets=1, continuationToken=response["continuationToken"]
    )

    assert len(response["tableBuckets"]) == 1
    assert "continuationToken" not in response
    assert response["tableBuckets"][0]["name"] == "bar"


@mock_aws
def test_get_table_bucket():
    client = boto3.client("s3tables", region_name="us-east-1")
    response = client.create_table_bucket(name="foo")

    assert client.get_table_bucket(tableBucketARN=response["arn"])["name"] == "foo"


@mock_aws
def test_delete_table_bucket():
    client = boto3.client("s3tables", region_name="us-east-1")
    arn = client.create_table_bucket(name="foo")["arn"]
    response = client.list_table_buckets()
    assert response["tableBuckets"]

    client.delete_table_bucket(tableBucketARN=arn)
    response = client.list_table_buckets()
    assert not response["tableBuckets"]


@mock_aws
def test_create_namespace():
    client = boto3.client("s3tables", region_name="us-east-1")
    arn = client.create_table_bucket(name="foo")["arn"]
    resp = client.create_namespace(tableBucketARN=arn, namespace=["bar"])

    assert resp["namespace"] == ["bar"]


@mock_aws
def test_list_namespaces():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["foo"])
    resp = client.list_namespaces(tableBucketARN=arn)
    assert resp["namespaces"]
    assert resp["namespaces"][0]["namespace"] == ["foo"]


@mock_aws
def test_list_namespaces_pagination():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["foo"])
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    response = client.list_namespaces(tableBucketARN=arn, maxNamespaces=1)

    assert len(response["namespaces"]) == 1
    assert "continuationToken" in response

    response = client.list_namespaces(
        tableBucketARN=arn,
        maxNamespaces=1,
        continuationToken=response["continuationToken"],
    )

    assert len(response["namespaces"]) == 1
    assert "continuationToken" not in response
    assert response["namespaces"][0]["namespace"] == ["bar"]


@mock_aws
def test_get_namespace():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.get_namespace(tableBucketARN=arn, namespace="bar")
    assert resp["namespace"] == ["bar"]


@mock_aws
def test_delete_namespace():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    assert client.list_namespaces(tableBucketARN=arn)["namespaces"]
    client.delete_namespace(tableBucketARN=arn, namespace="bar")
    assert not client.list_namespaces(tableBucketARN=arn)["namespaces"]


@mock_aws
def test_create_table():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )
    assert "tableARN" in resp
    assert "versionToken" in resp


@mock_aws
def test_get_table():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    table_arn = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )["tableARN"]

    assert (
        client.get_table(tableBucketARN=arn, namespace="bar", name="baz")["tableARN"]
        == table_arn
    )


@mock_aws
def test_list_tables():
    client = boto3.client("s3tables", region_name="us-east-2")
    resp = client.list_tables()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_table():
    client = boto3.client("s3tables", region_name="us-east-2")
    resp = client.delete_table()

    raise Exception("NotYetImplemented")
