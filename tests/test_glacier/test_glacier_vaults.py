from __future__ import unicode_literals

import boto.glacier
import sure  # noqa

from moto import mock_glacier_deprecated


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
