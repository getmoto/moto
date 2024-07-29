"""Unit tests for transfer-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.transfer.types import HomeDirectoryMapping


@pytest.fixture(name="client")
def fixture_transfer_client():
    with mock_aws():
        yield boto3.client("transfer", region_name="us-east-1")


@mock_aws
def test_create_describe_and_delete_user(client):
    home_directory_mapping: HomeDirectoryMapping = {"Entry": "/directory1", "Target": "/bucket_name/home/mydirectory"}
    connection = client.create_user(
        HomeDirectory="/Users/mock_user",
        HomeDirectoryType="PATH",
        HomeDirectoryMappings=[
           home_directory_mapping 
        ],
        Policy="MockPolicy",
        PosixProfile={
            "Uid": 0,
            "Gid": 1,
        },
        Role="TransferFamilyAdministrator",
        ServerId="123467890ABCDEFGHIJ",
        SshPublicKeyBody="ED25519",
        Tags=[{"Key": "Owner", "Value": "MotoUser1337"}],
        UserName="test_user",
    )
    user_name = connection["UserName"]
    server_id = connection["ServerId"]

    assert user_name == "test_user"
    assert server_id == "123467890ABCDEFGHIJ"

    connection = client.describe_user(UserName=user_name, ServerId=server_id)

    assert connection["ServerId"] == server_id
    user = connection["User"]
    assert user["HomeDirectory"] == "/Users/mock_user"
    assert user["HomeDirectoryType"] == "PATH"
    assert user["HomeDirectoryMappings"][0]["Entry"] == "/directory1"
    assert user["HomeDirectoryMappings"][0]["Target"] == "/bucket_name/home/mydirectory"
    assert user["Policy"] == "MockPolicy"
    assert user["PosixProfile"]["Uid"] == 0
    assert user["PosixProfile"]["Gid"] == 1
    assert user["Role"] == "TransferFamilyAdministrator"
    assert user["SshPublicKeys"][0]["SshPublicKeyBody"] == "ED25519"
    assert user["Tags"][0]["Key"] == "Owner"
    assert user["Tags"][0]["Value"] == "MotoUser1337"
    assert user["UserName"] == "test_user"

    client.delete_user(UserName=user_name, ServerId=server_id)

    with pytest.raises(ClientError):
        client.describe_user(UserName=user_name, ServerId=server_id)


@mock_aws
def test_import_and_delete_ssh_public_key(client):
    home_directory_mapping: HomeDirectoryMapping = {"Entry": "/directory1", "Target": "/bucket_name/home/mydirectory"}
    server_id = "123467890ABCDEFGHIJ"
    user_name = "test_user"
    client.create_user(
        HomeDirectory="/Users/mock_user",
        HomeDirectoryType="PATH",
        HomeDirectoryMappings=[
            home_directory_mapping
        ],
        Policy="MockPolicy",
        PosixProfile={
            "Uid": 0,
            "Gid": 1,
        },
        Role="TransferFamilyAdministrator",
        ServerId=server_id,
        SshPublicKeyBody="ED25519",
        Tags=[{"Key": "Owner", "Value": "MotoUser1337"}],
        UserName=user_name,
    )
    client.import_ssh_public_key(
        ServerId=server_id,
        SshPublicKeyBody="RSA",
        UserName=user_name,
    )
    connection = client.describe_user(UserName=user_name, ServerId=server_id)
    assert connection["User"]["SshPublicKeys"][-1]["SshPublicKeyBody"] == "RSA"
    client.delete_ssh_public_key(
        ServerId=server_id,
        UserName=user_name,
        SshPublicKeyId=connection["User"]["SshPublicKeys"][-1]["SshPublicKeyId"],
    )
    connection = client.describe_user(UserName=user_name, ServerId=server_id)
    assert connection["User"]["SshPublicKeys"][-1]["SshPublicKeyBody"] == "ED25519"
