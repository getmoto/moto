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
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    resp = client.list_tables(tableBucketARN=arn, namespace="bar")
    assert resp["tables"]
    assert resp["tables"][0]["name"] == "baz"


@mock_aws
def test_list_tables_pagination():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )
    client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz2", format="ICEBERG"
    )

    resp = client.list_tables(tableBucketARN=arn, maxTables=1)
    assert len(resp["tables"]) == 1
    assert "continuationToken" in resp

    resp = client.list_tables(
        tableBucketARN=arn, maxTables=1, continuationToken=resp["continuationToken"]
    )

    assert len(resp["tables"]) == 1
    assert "continuationToken" not in resp
    assert resp["tables"][0]["name"] == "baz2"


@mock_aws
def test_delete_table():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    resp = client.list_tables(tableBucketARN=arn)
    assert len(resp["tables"]) == 1

    client.delete_table(tableBucketARN=arn, namespace="bar", name="baz")

    resp = client.list_tables(tableBucketARN=arn)
    assert len(resp["tables"]) == 0


@mock_aws
def test_delete_table_deletes_underlying_table_storage():
    client = boto3.client("s3tables", region_name="us-east-2")
    s3 = boto3.client("s3", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )
    warehouse = client.get_table(tableBucketARN=arn, namespace="bar", name="baz")[
        "warehouseLocation"
    ]

    bucket_name = warehouse.replace("s3://", "")
    s3.head_bucket(Bucket=bucket_name)

    client.delete_table(tableBucketARN=arn, namespace="bar", name="baz")
    with pytest.raises(s3.exceptions.ClientError) as exc:
        s3.head_bucket(Bucket=bucket_name)
    exc.match("Not Found")


@mock_aws
def test_delete_table_fails_on_version_token_mismatch():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )
    token = resp["versionToken"]

    with pytest.raises(client.exceptions.ConflictException) as exc:
        client.delete_table(
            tableBucketARN=arn, namespace="bar", name="baz", versionToken=f"{token}-foo"
        )
    exc.match("Provided version token does not match the table version token.")


@mock_aws
def test_get_table_metadata_location():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )
    resp = client.get_table_metadata_location(
        tableBucketARN=arn, namespace="bar", name="baz"
    )
    assert "metadataLocation" not in resp
    assert "warehouseLocation" in resp


@mock_aws
def test_update_table_metadata_location():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )
    resp = client.get_table(tableBucketARN=arn, namespace="bar", name="baz")
    warehouse_location = resp["warehouseLocation"]
    client.update_table_metadata_location(
        tableBucketARN=arn,
        namespace="bar",
        name="baz",
        metadataLocation=f"{warehouse_location}/abc",
        versionToken=resp["versionToken"],
    )
    resp = client.get_table_metadata_location(
        tableBucketARN=arn, namespace="bar", name="baz"
    )
    assert "metadataLocation" in resp
    assert resp["metadataLocation"] == f"{warehouse_location}/abc"


@mock_aws
def test_update_table_metadata_location_raises_exception_on_invalid_path():
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )
    with pytest.raises(client.exceptions.BadRequestException) as exc:
        client.update_table_metadata_location(
            tableBucketARN=arn,
            namespace="bar",
            name="baz",
            metadataLocation="s3://abc",
            versionToken=resp["versionToken"],
        )
    exc.match("The specified metadata location is not valid.")


@mock_aws
def test_write_metadata_to_table() -> None:
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    resp = client.get_table(tableBucketARN=arn, namespace="bar", name="baz")
    s3 = boto3.client("s3", region_name="us-east-2")
    metadata = b'{"foo":"bar"}'

    bucket_name = resp["warehouseLocation"].replace("s3://", "")
    key = "metadata/00001-foo.metadata.json"
    s3.put_object(Bucket=bucket_name, Key=key, Body=metadata)

    client.update_table_metadata_location(
        tableBucketARN=arn,
        namespace="bar",
        name="baz",
        metadataLocation=f"s3://{bucket_name}/{key}",
        versionToken=resp["versionToken"],
    )
    resp = client.get_table_metadata_location(
        tableBucketARN=arn, namespace="bar", name="baz"
    )
    bucket, key = resp["metadataLocation"].replace("s3://", "").split("/", 1)
    resp = s3.get_object(Bucket=bucket, Key=key)
    assert resp["Body"].read() == metadata


@mock_aws
def test_underlying_table_storage_does_not_support_list_objects() -> None:
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    resp = client.get_table(tableBucketARN=arn, namespace="bar", name="baz")
    s3 = boto3.client("s3", region_name="us-east-2")

    bucket_name = resp["warehouseLocation"].replace("s3://", "")
    with pytest.raises(s3.exceptions.ClientError) as exc:
        s3.list_objects_v2(Bucket=bucket_name)
    assert exc.match("The specified method is not allowed against this resource.")


@mock_aws
def test_underlying_table_storage_does_not_support_delete_object() -> None:
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    resp = client.get_table(tableBucketARN=arn, namespace="bar", name="baz")
    s3 = boto3.client("s3", region_name="us-east-2")

    bucket_name = resp["warehouseLocation"].replace("s3://", "")
    s3.put_object(Bucket=bucket_name, Key="test", Body=b"{}")
    with pytest.raises(s3.exceptions.ClientError) as exc:
        s3.delete_object(Bucket=bucket_name, Key="test")
    assert exc.match("The specified method is not allowed against this resource.")


@mock_aws
def test_rename_table() -> None:
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    client.create_namespace(tableBucketARN=arn, namespace=["bar-two"])
    client.rename_table(
        tableBucketARN=arn,
        namespace="bar",
        name="baz",
        newNamespaceName="bar-two",
        newName="baz-two",
        versionToken=resp["versionToken"],
    )
    assert (
        client.get_table(tableBucketARN=arn, namespace="bar-two", name="baz-two")[
            "name"
        ]
        == "baz-two"
    )
    assert client.get_table(tableBucketARN=arn, namespace="bar-two", name="baz-two")[
        "namespace"
    ] == ["bar-two"]


@mock_aws
def test_rename_table_fails_when_destination_namespace_does_not_exist() -> None:
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    with pytest.raises(client.exceptions.NotFoundException) as ctx:
        client.rename_table(
            tableBucketARN=arn,
            namespace="bar",
            name="baz",
            newNamespaceName="bar-two",
            newName="baz-two",
            versionToken=resp["versionToken"],
        )
    assert ctx.match("The specified destination namespace does not exist.")


@mock_aws
def test_rename_table_fails_when_no_updates_are_specified() -> None:
    client = boto3.client("s3tables", region_name="us-east-2")
    arn = client.create_table_bucket(name="foo")["arn"]
    client.create_namespace(tableBucketARN=arn, namespace=["bar"])
    resp = client.create_table(
        tableBucketARN=arn, namespace="bar", name="baz", format="ICEBERG"
    )

    with pytest.raises(client.exceptions.BadRequestException) as ctx:
        client.rename_table(
            tableBucketARN=arn,
            namespace="bar",
            name="baz",
            versionToken=resp["versionToken"],
        )
    assert ctx.match("Neither a new namespace name nor a new table name is specified.")
