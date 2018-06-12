from __future__ import unicode_literals

import boto.kms
from moto.core import BaseBackend, BaseModel
from .utils import generate_key_id
from collections import defaultdict


class Key(BaseModel):

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

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
        if attribute_name == 'Arn':
            return self.arn
        raise UnformattedGetAttTemplateException()


class KmsBackend(BaseBackend):

    def __init__(self):
        self.keys = {}
        self.key_to_aliases = defaultdict(set)

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
        # allow the different methods (alias, ARN :key/, keyId, ARN alias) to
        # describe key not just KeyId
        key_id = self.get_key_id(key_id)
        if r'alias/' in str(key_id).lower():
            key_id = self.get_key_id_from_alias(key_id.split('alias/')[1])
        return self.keys[self.get_key_id(key_id)]

    def list_keys(self):
        return self.keys.values()

    def get_key_id(self, key_id):
        # Allow use of ARN as well as pure KeyId
        return str(key_id).split(r':key/')[1] if r':key/' in str(key_id).lower() else key_id

    def alias_exists(self, alias_name):
        for aliases in self.key_to_aliases.values():
            if alias_name in aliases:
                return True

        return False

    def add_alias(self, target_key_id, alias_name):
        self.key_to_aliases[target_key_id].add(alias_name)

    def delete_alias(self, alias_name):
        """Delete the alias."""
        for aliases in self.key_to_aliases.values():
            if alias_name in aliases:
                aliases.remove(alias_name)

    def get_all_aliases(self):
        return self.key_to_aliases

    def get_key_id_from_alias(self, alias_name):
        for key_id, aliases in dict(self.key_to_aliases).items():
            if alias_name in ",".join(aliases):
                return key_id
        return None

    def enable_key_rotation(self, key_id):
        self.keys[self.get_key_id(key_id)].key_rotation_status = True

    def disable_key_rotation(self, key_id):
        self.keys[self.get_key_id(key_id)].key_rotation_status = False

    def get_key_rotation_status(self, key_id):
        return self.keys[self.get_key_id(key_id)].key_rotation_status

    def put_key_policy(self, key_id, policy):
        self.keys[self.get_key_id(key_id)].policy = policy

    def get_key_policy(self, key_id):
        return self.keys[self.get_key_id(key_id)].policy


kms_backends = {}
for region in boto.kms.regions():
    kms_backends[region.name] = KmsBackend()
