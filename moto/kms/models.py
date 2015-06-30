from __future__ import unicode_literals

import boto.kms
from moto.core import BaseBackend
from .utils import generate_key_id


class Key(object):
    def __init__(self, policy, key_usage, description, region):
        self.id = generate_key_id()
        self.policy = policy
        self.key_usage = key_usage
        self.description = description
        self.enabled = True
        self.region = region
        self.account_id = "0123456789012"

    @property
    def arn(self):
        return "arn:aws:kms:{}:{}:key/{}".format(self.region, self.account_id, self.id)

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

    def create_key(self, policy, key_usage, description, region):
        key = Key(policy, key_usage, description, region)
        self.keys[key.id] = key
        return key

    def describe_key(self, key_id):
        return self.keys[key_id]

    def list_keys(self):
        return self.keys.values()

kms_backends = {}
for region in boto.kms.regions():
    kms_backends[region.name] = KmsBackend()
