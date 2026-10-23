import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_key_value_store():
    client = boto3.client("cloudfront", region_name="us-east-1")

    response = client.create_key_value_store(
        Name="test",
        Comment="Test key value store",
        Tags={"Items": [{"Key": "Environment", "Value": "Test"}]},
    )

    kv_store = response["KeyValueStore"]
    assert kv_store["Name"] == "test"
    assert kv_store["Comment"] == "Test key value store"
    assert kv_store["Id"]
    assert kv_store["ARN"].endswith(f"key-value-store/{kv_store['Id']}")
    assert response["ETag"]
    assert (
        response["Location"]
        == f"https://cloudfront.amazonaws.com/2020-05-31/key-value-store/{kv_store['Id']}"
    )
    tags = client.list_tags_for_resource(Resource=kv_store["ARN"])["Tags"]["Items"]
    assert tags == [{"Key": "Environment", "Value": "Test"}]


@mock_aws
def test_create_key_value_store_already_exists():
    client = boto3.client("cloudfront", region_name="us-east-1")

    client.create_key_value_store(Name="test", Comment="Test key value store")

    with pytest.raises(ClientError) as exc:
        client.create_key_value_store(Name="test", Comment="Test key value store")
    error = exc.value.response["Error"]
    assert error["Code"] == "EntityAlreadyExists"


@mock_aws
def test_describe_key_value_store():
    client = boto3.client("cloudfront", region_name="us-east-1")

    kv_store = client.create_key_value_store(
        Name="test", Comment="Test key value store"
    )["KeyValueStore"]

    response = client.describe_key_value_store(Name="test")
    assert response["KeyValueStore"] == kv_store


@mock_aws
def test_describe_key_value_store_not_found():
    client = boto3.client("cloudfront", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.describe_key_value_store(Name="test")
    error = exc.value.response["Error"]
    assert error["Code"] == "EntityNotFound"


@mock_aws
def test_list_key_value_stores():
    client = boto3.client("cloudfront", region_name="us-east-1")

    client.create_key_value_store(Name="test1", Comment="Test key value store 1")[
        "KeyValueStore"
    ]
    client.create_key_value_store(Name="test2", Comment="Test key value store 2")[
        "KeyValueStore"
    ]

    kv_stores = client.list_key_value_stores()["KeyValueStoreList"]
    assert kv_stores["Quantity"] == 2
    names = {s["Name"] for s in kv_stores["Items"]}
    assert names == {"test1", "test2"}


@mock_aws
def test_update_key_value_store():
    client = boto3.client("cloudfront", region_name="us-east-1")

    kv_store = client.create_key_value_store(
        Name="test", Comment="Test key value store"
    )["KeyValueStore"]

    response = client.update_key_value_store(
        Name="test", Comment="Updated comment", IfMatch=kv_store["ARN"]
    )

    updated_kv_store = response["KeyValueStore"]
    assert updated_kv_store["Name"] == "test"
    assert updated_kv_store["Comment"] == "Updated comment"
    assert updated_kv_store["Id"] == kv_store["Id"]
    assert updated_kv_store["ARN"] == kv_store["ARN"]


@mock_aws
def test_delete_key_value_store():
    client = boto3.client("cloudfront", region_name="us-east-1")

    kv_store = client.create_key_value_store(
        Name="test", Comment="Test key value store"
    )["KeyValueStore"]

    client.delete_key_value_store(Name="test", IfMatch=kv_store["ARN"])

    with pytest.raises(ClientError) as exc:
        client.describe_key_value_store(Name="test")
    error = exc.value.response["Error"]
    assert error["Code"] == "EntityNotFound"


@mock_aws
def test_list_key_value_stores_paginate():
    seen_tokens = set()
    client = boto3.client("cloudfront", region_name="us-east-1")
    expected_ids = {
        client.create_key_value_store(
            Name=f"test{index}", Comment=f"Test key value store {index}"
        )["KeyValueStore"]["Id"]
        for index in range(101)
    }
    response = client.list_key_value_stores()["KeyValueStoreList"]
    pages = [response["Items"]]
    assert len(pages[0]) == 100
    while response.get("NextMarker"):
        next_marker = response["NextMarker"]
        assert next_marker not in seen_tokens
        seen_tokens.add(next_marker)
        response = client.list_key_value_stores(Marker=next_marker)["KeyValueStoreList"]
        pages.append(response["Items"])
    ids = [store["Id"] for page in pages for store in page]
    assert [len(page) for page in pages] == [100, 1]
    assert len(ids) == 101
    assert set(ids) == expected_ids
