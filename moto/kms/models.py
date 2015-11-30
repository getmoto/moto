from __future__ import unicode_literals

import boto.kms
from moto.core import BaseBackend
from .utils import generate_key_id
from collections import defaultdict


class Key(object):
    def __init__(self, policy, key_usage, description, region):
        self.id = generate_key_id()
        self.policy = policy
        self.key_usage = key_usage
        self.description = description
        self.enabled = True
        self.region = region
        self.account_id = "0123456789012"
        self.key_rotation_status = False

    @property
    def arn(self):
        return "arn:aws:kms:{0}:{1}:key/{2}".format(self.region, self.account_id, self.id)

    def to_dict(self):
        return {
            "KeyMetadata": {
                "AWSAccountId": self.account_id,
                "Arn": self.arn,
                "CreationDate": "2015-01-01 00:00:00",
                "Description": self.description,
                "Enabled": self.enabled,
                "KeyId": self.id,
                "KeyUsage": self.key_usage,
            }
        }


class KmsBackend(BaseBackend):

    def __init__(self):
        self.keys = {}
        self.key_to_aliases = defaultdict(set)

    def create_key(self, policy, key_usage, description, region):
        key = Key(policy, key_usage, description, region)
        self.keys[key.id] = key
        return key

    def describe_key(self, key_id):
        return self.keys[key_id]

    def list_keys(self):
        return self.keys.values()

    def alias_exists(self, alias_name):
        for aliases in self.key_to_aliases.values():
            if alias_name in aliases:
                return True

        return False

    def add_alias(self, target_key_id, alias_name):
        self.key_to_aliases[target_key_id].add(alias_name)

    def delete_alias(self, alias_name):
        for aliases in self.key_to_aliases.values():
            aliases.remove(alias_name)

    def get_all_aliases(self):
        return self.key_to_aliases

    def enable_key_rotation(self, key_id):
        self.keys[key_id].key_rotation_status = True

    def disable_key_rotation(self, key_id):
        self.keys[key_id].key_rotation_status = False

    def get_key_rotation_status(self, key_id):
        return self.keys[key_id].key_rotation_status

    def put_key_policy(self, key_id, policy):
        self.keys[key_id].policy = policy

    def get_key_policy(self, key_id):
        return self.keys[key_id].policy


kms_backends = {}
for region in boto.kms.regions():
    kms_backends[region.name] = KmsBackend()
