from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_describe_vault():
    client = boto3.client("glacier", region_name="us-west-2")

    client.create_vault(vaultName="myvault")

    describe = client.describe_vault(vaultName="myvault")
    assert describe["NumberOfArchives"] == 0
    assert describe["SizeInBytes"] == 0
    assert "LastInventoryDate" in describe
    assert "CreationDate" in describe
    assert describe["VaultName"] == "myvault"
    assert (
        describe["VaultARN"] == f"arn:aws:glacier:us-west-2:{ACCOUNT_ID}:vaults/myvault"
    )


@mock_aws
def test_delete_vault_boto3():
    client = boto3.client("glacier", region_name="us-west-2")

    client.create_vault(vaultName="myvault")

    client.delete_vault(vaultName="myvault")

    with pytest.raises(ClientError) as exc:
        client.describe_vault(vaultName="myvault")
    err = exc.value.response["Error"]
    assert err["Code"] == "VaultNotFound"


@mock_aws
def test_list_vaults():
    client = boto3.client("glacier", region_name="us-west-2")

    vault1_name = str(uuid4())[0:6]
    vault2_name = str(uuid4())[0:6]

    # Verify we cannot find these vaults yet
    vaults = client.list_vaults()["VaultList"]
    found_vaults = [v["VaultName"] for v in vaults]
    assert vault1_name not in found_vaults
    assert vault2_name not in found_vaults

    client.create_vault(vaultName=vault1_name)
    client.create_vault(vaultName=vault2_name)

    # Verify we can find the created vaults
    vaults = client.list_vaults()["VaultList"]
    found_vaults = [v["VaultName"] for v in vaults]
    assert vault1_name in found_vaults
    assert vault2_name in found_vaults

    # Verify all the vaults are in the correct format
    for vault in vaults:
        assert vault["NumberOfArchives"] == 0
        assert vault["SizeInBytes"] == 0
        assert "LastInventoryDate" in vault
        assert "CreationDate" in vault
        assert "VaultName" in vault
        vault_name = vault["VaultName"]
        assert (
            vault["VaultARN"]
            == f"arn:aws:glacier:us-west-2:{ACCOUNT_ID}:vaults/{vault_name}"
        )

    # Verify a deleted vault is no longer returned
    client.delete_vault(vaultName=vault1_name)

    vaults = client.list_vaults()["VaultList"]
    found_vaults = [v["VaultName"] for v in vaults]
    assert vault1_name not in found_vaults
    assert vault2_name in found_vaults


@mock_aws
def test_vault_name_with_special_characters():
    vault_name = "Vault.name-with_Special.characters"
    glacier = boto3.resource("glacier", region_name="us-west-2")
    vault = glacier.create_vault(accountId="-", vaultName=vault_name)
    assert vault.name == vault_name
