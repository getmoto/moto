from __future__ import unicode_literals

import boto.glacier
import boto3
import sure  # noqa

from moto import mock_glacier_deprecated, mock_glacier


@mock_glacier_deprecated
def test_create_vault():
    conn = boto.glacier.connect_to_region("us-west-2")

    conn.create_vault("my_vault")

    vaults = conn.list_vaults()
    vaults.should.have.length_of(1)
    vaults[0].name.should.equal("my_vault")


@mock_glacier_deprecated
def test_delete_vault():
    conn = boto.glacier.connect_to_region("us-west-2")

    conn.create_vault("my_vault")

    vaults = conn.list_vaults()
    vaults.should.have.length_of(1)

    conn.delete_vault("my_vault")
    vaults = conn.list_vaults()
    vaults.should.have.length_of(0)


@mock_glacier
def test_vault_name_with_special_characters():
    vault_name = "Vault.name-with_Special.characters"
    glacier = boto3.resource("glacier", region_name="us-west-2")
    vault = glacier.create_vault(accountId="-", vaultName=vault_name)
    vault.name.should.equal(vault_name)
