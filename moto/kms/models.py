from __future__ import unicode_literals

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

from boto3 import Session

from moto.core import ACCOUNT_ID, BaseBackend, CloudFormationModel
from moto.core.utils import unix_time
from moto.utilities.tagging_service import TaggingService
from moto.core.exceptions import JsonRESTError

from .utils import decrypt, encrypt, generate_key_id, generate_master_key


class Key(CloudFormationModel):
    def __init__(
        self, policy, key_usage, customer_master_key_spec, description, region
    ):
        self.id = generate_key_id()
        self.creation_date = unix_time()
        self.policy = policy or self.generate_default_policy()
        self.key_usage = key_usage
        self.key_state = "Enabled"
        self.description = description or ""
        self.enabled = True
        self.region = region
        self.account_id = ACCOUNT_ID
        self.key_rotation_status = False
        self.deletion_date = None
        self.key_material = generate_master_key()
        self.origin = "AWS_KMS"
        self.key_manager = "CUSTOMER"
        self.customer_master_key_spec = customer_master_key_spec or "SYMMETRIC_DEFAULT"

    def generate_default_policy(self):
        return json.dumps(
            {
                "Version": "2012-10-17",
                "Id": "key-default-1",
                "Statement": [
                    {
                        "Sid": "Enable IAM User Permissions",
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
                        "Action": "kms:*",
                        "Resource": "*",
                    }
                ],
            }
        )

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def arn(self):
        return "arn:aws:kms:{0}:{1}:key/{2}".format(
            self.region, self.account_id, self.id
        )

    @property
    def encryption_algorithms(self):
        if self.key_usage == "SIGN_VERIFY":
            return None
        elif self.customer_master_key_spec == "SYMMETRIC_DEFAULT":
            return ["SYMMETRIC_DEFAULT"]
        else:
            return ["RSAES_OAEP_SHA_1", "RSAES_OAEP_SHA_256"]

    @property
    def signing_algorithms(self):
        if self.key_usage == "ENCRYPT_DECRYPT":
            return None
        elif self.customer_master_key_spec in ["ECC_NIST_P256", "ECC_SECG_P256K1"]:
            return ["ECDSA_SHA_256"]
        elif self.customer_master_key_spec == "ECC_NIST_P384":
            return ["ECDSA_SHA_384"]
        elif self.customer_master_key_spec == "ECC_NIST_P521":
            return ["ECDSA_SHA_512"]
        else:
            return [
                "RSASSA_PKCS1_V1_5_SHA_256",
                "RSASSA_PKCS1_V1_5_SHA_384",
                "RSASSA_PKCS1_V1_5_SHA_512",
                "RSASSA_PSS_SHA_256",
                "RSASSA_PSS_SHA_384",
                "RSASSA_PSS_SHA_512",
            ]

    def to_dict(self):
        key_dict = {
            "KeyMetadata": {
                "AWSAccountId": self.account_id,
                "Arn": self.arn,
                "CreationDate": self.creation_date,
                "CustomerMasterKeySpec": self.customer_master_key_spec,
                "Description": self.description,
                "Enabled": self.enabled,
                "EncryptionAlgorithms": self.encryption_algorithms,
                "KeyId": self.id,
                "KeyManager": self.key_manager,
                "KeyUsage": self.key_usage,
                "KeyState": self.key_state,
                "Origin": self.origin,
                "SigningAlgorithms": self.signing_algorithms,
            }
        }
        if self.key_state == "PendingDeletion":
            key_dict["KeyMetadata"]["DeletionDate"] = unix_time(self.deletion_date)
        return key_dict

    def delete(self, region_name):
        kms_backends[region_name].delete_key(self.id)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-kms-key.html
        return "AWS::KMS::Key"

    @classmethod
    def create_from_cloudformation_json(
        self, resource_name, cloudformation_json, region_name
    ):
        kms_backend = kms_backends[region_name]
        properties = cloudformation_json["Properties"]

        key = kms_backend.create_key(
            policy=properties["KeyPolicy"],
            key_usage="ENCRYPT_DECRYPT",
            customer_master_key_spec="SYMMETRIC_DEFAULT",
            description=properties["Description"],
            tags=properties.get("Tags", []),
            region=region_name,
        )
        key.key_rotation_status = properties["EnableKeyRotation"]
        key.enabled = properties["Enabled"]

        return key

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        raise UnformattedGetAttTemplateException()


class KmsBackend(BaseBackend):
    def __init__(self):
        self.keys = {}
        self.key_to_aliases = defaultdict(set)
        self.tagger = TaggingService(key_name="TagKey", value_name="TagValue")

    def create_key(
        self, policy, key_usage, customer_master_key_spec, description, tags, region
    ):
        key = Key(policy, key_usage, customer_master_key_spec, description, region)
        self.keys[key.id] = key
        if tags is not None and len(tags) > 0:
            self.tag_resource(key.id, tags)
        return key

    def update_key_description(self, key_id, description):
        key = self.keys[self.get_key_id(key_id)]
        key.description = description

    def delete_key(self, key_id):
        if key_id in self.keys:
            if key_id in self.key_to_aliases:
                self.key_to_aliases.pop(key_id)
            self.tagger.delete_all_tags_for_resource(key_id)

            return self.keys.pop(key_id)

    def describe_key(self, key_id):
        # allow the different methods (alias, ARN :key/, keyId, ARN alias) to
        # describe key not just KeyId
        key_id = self.get_key_id(key_id)
        if r"alias/" in str(key_id).lower():
            key_id = self.get_key_id_from_alias(key_id.split("alias/")[1])
        return self.keys[self.get_key_id(key_id)]

    def list_keys(self):
        return self.keys.values()

    @staticmethod
    def get_key_id(key_id):
        # Allow use of ARN as well as pure KeyId
        if key_id.startswith("arn:") and ":key/" in key_id:
            return key_id.split(":key/")[1]

        return key_id

    @staticmethod
    def get_alias_name(alias_name):
        # Allow use of ARN as well as alias name
        if alias_name.startswith("arn:") and ":alias/" in alias_name:
            return alias_name.split(":alias/")[1]

        return alias_name

    def any_id_to_key_id(self, key_id):
        """Go from any valid key ID to the raw key ID.

        Acceptable inputs:
        - raw key ID
        - key ARN
        - alias name
        - alias ARN
        """
        key_id = self.get_alias_name(key_id)
        key_id = self.get_key_id(key_id)
        if key_id.startswith("alias/"):
            key_id = self.get_key_id_from_alias(key_id)
        return key_id

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

    def disable_key(self, key_id):
        self.keys[key_id].enabled = False
        self.keys[key_id].key_state = "Disabled"

    def enable_key(self, key_id):
        self.keys[key_id].enabled = True
        self.keys[key_id].key_state = "Enabled"

    def cancel_key_deletion(self, key_id):
        self.keys[key_id].key_state = "Disabled"
        self.keys[key_id].deletion_date = None

    def schedule_key_deletion(self, key_id, pending_window_in_days):
        if 7 <= pending_window_in_days <= 30:
            self.keys[key_id].enabled = False
            self.keys[key_id].key_state = "PendingDeletion"
            self.keys[key_id].deletion_date = datetime.now() + timedelta(
                days=pending_window_in_days
            )
            return unix_time(self.keys[key_id].deletion_date)

    def encrypt(self, key_id, plaintext, encryption_context):
        key_id = self.any_id_to_key_id(key_id)

        ciphertext_blob = encrypt(
            master_keys=self.keys,
            key_id=key_id,
            plaintext=plaintext,
            encryption_context=encryption_context,
        )
        arn = self.keys[key_id].arn
        return ciphertext_blob, arn

    def decrypt(self, ciphertext_blob, encryption_context):
        plaintext, key_id = decrypt(
            master_keys=self.keys,
            ciphertext_blob=ciphertext_blob,
            encryption_context=encryption_context,
        )
        arn = self.keys[key_id].arn
        return plaintext, arn

    def re_encrypt(
        self,
        ciphertext_blob,
        source_encryption_context,
        destination_key_id,
        destination_encryption_context,
    ):
        destination_key_id = self.any_id_to_key_id(destination_key_id)

        plaintext, decrypting_arn = self.decrypt(
            ciphertext_blob=ciphertext_blob,
            encryption_context=source_encryption_context,
        )
        new_ciphertext_blob, encrypting_arn = self.encrypt(
            key_id=destination_key_id,
            plaintext=plaintext,
            encryption_context=destination_encryption_context,
        )
        return new_ciphertext_blob, decrypting_arn, encrypting_arn

    def generate_data_key(
        self, key_id, encryption_context, number_of_bytes, key_spec, grant_tokens
    ):
        key_id = self.any_id_to_key_id(key_id)

        if key_spec:
            # Note: Actual validation of key_spec is done in kms.responses
            if key_spec == "AES_128":
                plaintext_len = 16
            else:
                plaintext_len = 32
        else:
            plaintext_len = number_of_bytes

        plaintext = os.urandom(plaintext_len)

        ciphertext_blob, arn = self.encrypt(
            key_id=key_id, plaintext=plaintext, encryption_context=encryption_context
        )

        return plaintext, ciphertext_blob, arn

    def list_resource_tags(self, key_id_or_arn):
        key_id = self.get_key_id(key_id_or_arn)
        if key_id in self.keys:
            return self.tagger.list_tags_for_resource(key_id)
        raise JsonRESTError(
            "NotFoundException",
            "The request was rejected because the specified entity or resource could not be found.",
        )

    def tag_resource(self, key_id_or_arn, tags):
        key_id = self.get_key_id(key_id_or_arn)
        if key_id in self.keys:
            self.tagger.tag_resource(key_id, tags)
            return {}
        raise JsonRESTError(
            "NotFoundException",
            "The request was rejected because the specified entity or resource could not be found.",
        )

    def untag_resource(self, key_id_or_arn, tag_names):
        key_id = self.get_key_id(key_id_or_arn)
        if key_id in self.keys:
            self.tagger.untag_resource_using_names(key_id, tag_names)
            return {}
        raise JsonRESTError(
            "NotFoundException",
            "The request was rejected because the specified entity or resource could not be found.",
        )


kms_backends = {}
for region in Session().get_available_regions("kms"):
    kms_backends[region] = KmsBackend()
for region in Session().get_available_regions("kms", partition_name="aws-us-gov"):
    kms_backends[region] = KmsBackend()
for region in Session().get_available_regions("kms", partition_name="aws-cn"):
    kms_backends[region] = KmsBackend()
