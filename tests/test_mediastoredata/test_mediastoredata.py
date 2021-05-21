from __future__ import unicode_literals

import boto3
import pytest
import sure  # noqa
from botocore.exceptions import ClientError

from moto import mock_mediastoredata

region = "eu-west-1"


@mock_mediastoredata
def test_put_object():
    client = boto3.client("mediastore-data", region_name=region)
    response = client.put_object(Body="011001", Path="foo")
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["StorageClass"].should.equal('TEMPORAL')
    # TODO: Why List_items is executing moto get_object instead list_items implementation?
    items = client.list_items()
    # object_exists = any(d["Name"] == "foo" for d in items)
    # object_exists.should.equal(True)


@mock_mediastoredata
def test_get_object():
    client = boto3.client("mediastore-data", region_name=region)
    response = client.get_object(Path="foo")
    pass


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
    new_object = client.put_object(Body="011001", Path=object_path)
    response = client.delete_object(Path=object_path)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    items = client.list_items(NextToken="next-token")["Containers"]
    # object_exists = any(d["Name"] == object_path for d in items)
    # object_exists.should.equal(False)


@mock_mediastoredata
def test_list_items():
    client = boto3.client("mediastore-data", region_name=region)
    # TODO: Why List_items is executing moto get_object instead list_items implementation?
    items = client.list_items()
    items.should.equal(False)
