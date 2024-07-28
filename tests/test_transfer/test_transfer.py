"""Unit tests for transfer-supported APIs."""

import boto3
import pytest

from moto import mock_aws
from moto.transfer.exceptions import UserNotFound


@pytest.fixture(name="client")
def fixture_transfer_client():
    with mock_aws():
        yield boto3.client("transfer", region_name="us-east-1")


@mock_aws
def test_create_describe_and_delete_user(client):
    connection = client.create_user(
        HomeDirectory="/Users/mock_user",
        HomeDirectoryType="PATH",
        HomeDirectoryMappings=[{ "Entry": "/directory1", "Target": "/bucket_name/home/mydirectory" }],
        Policy="MockPolicy",
        PosixProfile={
            'Uid': 0,
            'Gid': 1,
        },
        Role="TransferFamilyAdministrator",
        ServerId="123467890ABCDEFGHIJ",
        SshPublicKeyBody="ED25519",
        Tags=[{'Key': 'Owner', 'Value': 'MotoUser1337'}],
        UserName="test_user"
    )
    user_name = connection["userName"]
    server_id = connection["serverId"]

    assert user_name == "test_user"
    assert server_id == "1234"

    connection = client.describe_user(
        user_name=user_name,
        server_id=server_id
    )

    assert connection["serverId"] == server_id
    user = connection["user"]
    assert user["HomeDirectory"] == "/Users/mock_user"
    assert user["HomeDirectoryType"] == "PATH"
    assert user["HomeDirectoryMappings"]["Entry"] == "/directory1"
    assert user["HomeDirectoryMappings"]["Target"] == "/bucket_name/home/mydirectory"
    assert user["Policy"] == "MockPolicy"
    assert user["PosixProfile"]['Uid'] == 0
    assert user["PosixProfile"]['Gid'] == 1
    assert user["Role"] == "TransferFamilyAdministrator"
    assert user["ServerId"] == "123467890ABCDEFGHIJ"
    assert user["SshPublicKeys"][0]["SshPublicKeyBody"] == "ED25519"
    assert user["Tags"][0]["Key"] == "Owner"
    assert user["Tags"][0]["Value"] == "MotoUser1337"
    assert user["UserName"] == "test_user"
    
    client.delete_user(
        user_name=user_name,
        server_id=server_id
    )
    
    with pytest.raises(UserNotFound):
        client.describe_user(
            user_name=user_name,
            server_id=server_id
        )
       

@mock_aws
@pytest.mark.skip(reason="TODO")
def test_import_ssh_public_key():
    client = boto3.client("transfer", region_name="us-east-2")
    resp = client.import_ssh_public_key()

    raise Exception("NotYetImplemented")


@mock_aws
@pytest.mark.skip(reason="TODO")
def test_delete_ssh_public_key():
    client = boto3.client("transfer", region_name="us-east-1")
    resp = client.delete_ssh_public_key()

    raise Exception("NotYetImplemented")
