from __future__ import unicode_literals

import boto.glacier
from moto.core import BaseBackend


class Vault(object):
    def __init__(self, vault_name, region):
        self.vault_name = vault_name
        self.region = region

    @property
    def arn(self):
        return "arn:aws:glacier:{}:012345678901:vaults/{}".format(self.region, self.vault_name)

    def to_dict(self):
        return {
            "CreationDate": "2013-03-20T17:03:43.221Z",
            "LastInventoryDate": "2013-03-20T17:03:43.221Z",
            "NumberOfArchives": None,
            "SizeInBytes": None,
            "VaultARN": self.arn,
            "VaultName": self.vault_name,
        }


class GlacierBackend(BaseBackend):

    def __init__(self, region_name):
        self.vaults = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def get_vault(self, vault_name):
        return self.vaults[vault_name]

    def create_vault(self, vault_name):
        self.vaults[vault_name] = Vault(vault_name, self.region_name)

    def list_vaules(self):
        return self.vaults.values()

    def delete_vault(self, vault_name):
        self.vaults.pop(vault_name)

glacier_backends = {}
for region in boto.glacier.regions():
    glacier_backends[region.name] = GlacierBackend(region)
