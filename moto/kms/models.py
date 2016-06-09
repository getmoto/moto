from __future__ import unicode_literals

import os

import boto.kms
from moto.core import BaseBackend
from .utils import generate_key_id
from .exceptions import InvalidKeyUsageError
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
    def physical_resource_id(self):
        return self.id

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

    def delete(self, region_name):
        kms_backends[region_name].delete_key(self.id)

    @classmethod
    def create_from_cloudformation_json(self, resource_name, cloudformation_json, region_name):
        kms_backend = kms_backends[region_name]
        properties = cloudformation_json['Properties']

        key = kms_backend.create_key(
            policy=properties['KeyPolicy'],
            key_usage='ENCRYPT_DECRYPT',
            description=properties['Description'],
            region=region_name,
        )
        key.key_rotation_status = properties['EnableKeyRotation']
        key.enabled = properties['Enabled']

        return key


class KmsBackend(BaseBackend):

    def __init__(self):
        self.keys = {}
        self.key_to_aliases = defaultdict(set)
        self.encryption_map = {}

    def create_key(self, policy, key_usage, description, region):
        key = Key(policy, key_usage, description, region)
        self.keys[key.id] = key
        return key

    def delete_key(self, key_id):
        if key_id in self.keys:
            if key_id in self.key_to_aliases:
                self.key_to_aliases.pop(key_id)

            return self.keys.pop(key_id)

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

    def encrypt(self, key_id, plaintext, encryption_context):
        ciphertext = os.urandom(512)

        if encryption_context:
            # The encryption context needs to be turned into a tuple so that it can be used as a
            # key. It is sorted so that the tuple is always the same, given the same dictionary.
            immutable_encryption_context = tuple(sorted(encryption_context.items()))
        else:
            immutable_encryption_context = None

        self.encryption_map[(ciphertext, immutable_encryption_context)] = (key_id, plaintext)

        return key_id, ciphertext

    def decrypt(self, ciphertext, encryption_context):
        if encryption_context:
            immutable_encryption_context = tuple(sorted(encryption_context.items()))
        else:
            immutable_encryption_context = None

        return self.encryption_map[(ciphertext, immutable_encryption_context)]

    def generate_data_key(self, key_id, key_spec=None, number_of_bytes=None, encryption_context=None):
        if number_of_bytes:
            raise NotImplementedError

        if key_spec == 'AES_128':
            plaintext = os.urandom(16)
        elif key_spec == 'AES_256':
            plaintext = os.urandom(32)
        else:
            raise InvalidKeyUsageError(key_spec)

        __, ciphertext = self.encrypt(key_id=key_id, plaintext=plaintext, encryption_context=encryption_context)

        return plaintext, key_id, ciphertext



kms_backends = {}
for region in boto.kms.regions():
    kms_backends[region.name] = KmsBackend()
