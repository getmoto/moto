import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_mediastoredata

region = "eu-west-1"


@mock_mediastoredata
def test_put_object():
    client = boto3.client("mediastore-data", region_name=region)
    response = client.put_object(Body="011001", Path="foo")
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["StorageClass"] == "TEMPORAL"

    items = client.list_items()["Items"]
    assert any(d["Name"] == "foo" for d in items)


@mock_mediastoredata
def test_get_object_throws_not_found_error():
    client = boto3.client("mediastore-data", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_object(Path="foo")
    assert ex.value.response["Error"]["Code"] == "ObjectNotFoundException"


@mock_mediastoredata
def test_get_object():
    client = boto3.client("mediastore-data", region_name=region)
    client.put_object(Body="011001", Path="foo")
    response = client.get_object(Path="foo")
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["ResponseMetadata"]["HTTPHeaders"]["path"] == "foo"
    assert response["Body"].read() == b"011001"


@mock_mediastoredata
def test_delete_object_error():
    client = boto3.client("mediastore-data", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.delete_object(Path="foo")
    assert ex.value.response["Error"]["Code"] == "ObjectNotFoundException"


@mock_mediastoredata
def test_delete_object_succeeds():
    client = boto3.client("mediastore-data", region_name=region)
    object_path = "foo"
    client.put_object(Body="011001", Path=object_path)
    response = client.delete_object(Path=object_path)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    assert len(client.list_items()["Items"]) == 0


@mock_mediastoredata
def test_list_items():
    client = boto3.client("mediastore-data", region_name=region)
    assert len(client.list_items()["Items"]) == 0

    object_path = "foo"
    client.put_object(Body="011001", Path=object_path)

    items = client.list_items()["Items"]
    assert len(items) == 1
    assert any(d["Name"] == object_path for d in items)
