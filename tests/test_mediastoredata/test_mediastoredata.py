import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_mediastoredata

region = "eu-west-1"


@mock_mediastoredata
def test_put_object():
    client = boto3.client("mediastore-data", region_name=region)
    response = client.put_object(Body="011001", Path="foo")
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["StorageClass"].should.equal("TEMPORAL")
    items = client.list_items()["Items"]
    object_exists = any(d["Name"] == "foo" for d in items)
    object_exists.should.equal(True)


@mock_mediastoredata
def test_get_object_throws_not_found_error():
    client = boto3.client("mediastore-data", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.get_object(Path="foo")
    ex.value.response["Error"]["Code"].should.equal("ObjectNotFoundException")


@mock_mediastoredata
def test_get_object():
    client = boto3.client("mediastore-data", region_name=region)
    client.put_object(Body="011001", Path="foo")
    response = client.get_object(Path="foo")
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["ResponseMetadata"]["HTTPHeaders"]["path"].should.equal("foo")
    data = response["Body"].read()
    data.should.equal(b"011001")


@mock_mediastoredata
def test_delete_object_error():
    client = boto3.client("mediastore-data", region_name=region)
    with pytest.raises(ClientError) as ex:
        client.delete_object(Path="foo")
    ex.value.response["Error"]["Code"].should.equal("ObjectNotFoundException")


@mock_mediastoredata
def test_delete_object_succeeds():
    client = boto3.client("mediastore-data", region_name=region)
    object_path = "foo"
    client.put_object(Body="011001", Path=object_path)
    response = client.delete_object(Path=object_path)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    items = client.list_items()["Items"]
    len(items).should.equal(0)


@mock_mediastoredata
def test_list_items():
    client = boto3.client("mediastore-data", region_name=region)
    items = client.list_items()["Items"]
    len(items).should.equal(0)
    object_path = "foo"
    client.put_object(Body="011001", Path=object_path)
    items = client.list_items()["Items"]
    len(items).should.equal(1)
    object_exists = any(d["Name"] == object_path for d in items)
    object_exists.should.equal(True)
