import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_glacier
from moto.core import ACCOUNT_ID
from uuid import uuid4


@mock_glacier
def test_describe_vault():
    client = boto3.client("glacier", region_name="us-west-2")

    client.create_vault(vaultName="myvault")

    describe = client.describe_vault(vaultName="myvault")
    describe.should.have.key("NumberOfArchives").equal(0)
    describe.should.have.key("SizeInBytes").equal(0)
    describe.should.have.key("LastInventoryDate")
    describe.should.have.key("CreationDate")
    describe.should.have.key("VaultName").equal("myvault")
    describe.should.have.key("VaultARN").equal(
        f"arn:aws:glacier:us-west-2:{ACCOUNT_ID}:vaults/myvault"
    )


@mock_glacier
def test_delete_vault_boto3():
    client = boto3.client("glacier", region_name="us-west-2")

    client.create_vault(vaultName="myvault")

    client.delete_vault(vaultName="myvault")

    with pytest.raises(Exception):
        client.describe_vault(vaultName="myvault")


@mock_glacier
def test_list_vaults():
    client = boto3.client("glacier", region_name="us-west-2")

    vault1_name = str(uuid4())[0:6]
    vault2_name = str(uuid4())[0:6]

    # Verify we cannot find these vaults yet
    vaults = client.list_vaults()["VaultList"]
    found_vaults = [v["VaultName"] for v in vaults]
    found_vaults.shouldnt.contain(vault1_name)
    found_vaults.shouldnt.contain(vault2_name)

    client.create_vault(vaultName=vault1_name)
    client.create_vault(vaultName=vault2_name)

    # Verify we can find the created vaults
    vaults = client.list_vaults()["VaultList"]
    found_vaults = [v["VaultName"] for v in vaults]
    found_vaults.should.contain(vault1_name)
    found_vaults.should.contain(vault2_name)

    # Verify all the vaults are in the correct format
    for vault in vaults:
        vault.should.have.key("NumberOfArchives").equal(0)
        vault.should.have.key("SizeInBytes").equal(0)
        vault.should.have.key("LastInventoryDate")
        vault.should.have.key("CreationDate")
        vault.should.have.key("VaultName")
        vault_name = vault["VaultName"]
        vault.should.have.key("VaultARN").equal(
            f"arn:aws:glacier:us-west-2:{ACCOUNT_ID}:vaults/{vault_name}"
        )

    # Verify a deleted vault is no longer returned
    client.delete_vault(vaultName=vault1_name)

    vaults = client.list_vaults()["VaultList"]
    found_vaults = [v["VaultName"] for v in vaults]
    found_vaults.shouldnt.contain(vault1_name)
    found_vaults.should.contain(vault2_name)


@mock_glacier
def test_vault_name_with_special_characters():
    vault_name = "Vault.name-with_Special.characters"
    glacier = boto3.resource("glacier", region_name="us-west-2")
    vault = glacier.create_vault(accountId="-", vaultName=vault_name)
    vault.name.should.equal(vault_name)
