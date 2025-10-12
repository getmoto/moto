"""Unit tests for qldb-supported APIs."""

from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@pytest.fixture(name="client")
def fixture_qldb_client():
    with mock_aws():
        yield boto3.client("qldb", region_name="us-east-1")


@mock_aws
def test_create_describe_update_and_delete_ledger(client):
    name = "mock_ledger"
    permissions_mode = "STANDARD"
    kms_key = "mock_key"
    connection = client.create_ledger(
        Name=name,
        PermissionsMode=permissions_mode,
        DeletionProtection=True,
        KmsKey=kms_key,
    )
    assert connection["Name"] == name
    assert connection["Arn"] == f"arn:aws:qldb:us-east-1:123456789012:ledger/{name}"
    assert (
        connection["KmsKeyArn"] == f"arn:aws:kms:us-east-1:123456789012:key/{kms_key}"
    )
    assert connection["PermissionsMode"] == permissions_mode
    assert isinstance(connection["CreationDateTime"], datetime)
    assert connection["DeletionProtection"]
    assert connection["State"] == "ACTIVE"

    connection = client.describe_ledger(Name=name)
    assert connection["Name"] == name
    assert connection["Arn"] == f"arn:aws:qldb:us-east-1:123456789012:ledger/{name}"
    assert connection["PermissionsMode"] == permissions_mode
    assert isinstance(connection["CreationDateTime"], datetime)
    assert connection["DeletionProtection"]
    assert connection["State"] == "ACTIVE"
    assert (
        connection["EncryptionDescription"]["KmsKeyArn"]
        == f"arn:aws:kms:us-east-1:123456789012:key/{kms_key}"
    )
    assert connection["EncryptionDescription"]["EncryptionStatus"] == "ENABLED"

    new_key = "new_mock_key"
    connection = client.update_ledger(
        Name=name, DeletionProtection=False, KmsKey=new_key
    )
    connection = client.describe_ledger(Name=name)
    assert connection["Name"] == name
    assert connection["Arn"] == f"arn:aws:qldb:us-east-1:123456789012:ledger/{name}"
    assert connection["PermissionsMode"] == permissions_mode
    assert isinstance(connection["CreationDateTime"], datetime)
    assert not connection["DeletionProtection"]
    assert connection["State"] == "ACTIVE"
    assert (
        connection["EncryptionDescription"]["KmsKeyArn"]
        == f"arn:aws:kms:us-east-1:123456789012:key/{new_key}"
    )
    assert connection["EncryptionDescription"]["EncryptionStatus"] == "ENABLED"

    connection = client.describe_ledger(Name=name)
    assert connection["Name"] == name
    assert connection["Arn"] == f"arn:aws:qldb:us-east-1:123456789012:ledger/{name}"
    assert connection["PermissionsMode"] == permissions_mode
    assert isinstance(connection["CreationDateTime"], datetime)
    assert not connection["DeletionProtection"]
    assert connection["State"] == "ACTIVE"
    assert (
        connection["EncryptionDescription"]["KmsKeyArn"]
        == f"arn:aws:kms:us-east-1:123456789012:key/{new_key}"
    )
    assert connection["EncryptionDescription"]["EncryptionStatus"] == "ENABLED"

    connection = client.delete_ledger(Name=name)
    with pytest.raises(ClientError) as e:
        client.describe_ledger(Name=name)
    err = e.value.response["Error"]
    assert err["Code"] == "LedgerNotFound"
    assert err["Message"] == f"{name} does not match any existing ledger."


@mock_aws
def test_tag_resource_and_list_tags_for_resource(client):
    name = "mock_ledger"
    tags = {"key1": "value1", "key2": "value2"}
    permissions_mode = "STANDARD"
    kms_key = "mock_key"
    connection = client.create_ledger(
        Name=name,
        Tags=tags,
        PermissionsMode=permissions_mode,
        DeletionProtection=True,
        KmsKey=kms_key,
    )
    arn = connection["Arn"]

    connection = client.list_tags_for_resource(ResourceArn=arn)
    assert connection["Tags"]["key1"] == "value1"
    assert connection["Tags"]["key2"] == "value2"
    assert "key3" not in connection["Tags"]
    client.tag_resource(ResourceArn=arn, Tags={"key3": "value3"})
    connection = client.list_tags_for_resource(ResourceArn=arn)
    assert connection["Tags"]["key1"] == "value1"
    assert connection["Tags"]["key2"] == "value2"
    assert connection["Tags"]["key3"] == "value3"
