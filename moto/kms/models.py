import json
import os
from collections import defaultdict
from copy import copy
from datetime import datetime, timedelta
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes

from cryptography.hazmat.primitives.asymmetric import padding

from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import unix_time, BackendDict
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService
from moto.core.exceptions import JsonRESTError

from .exceptions import ValidationException
from .utils import (
    RESERVED_ALIASES,
    decrypt,
    encrypt,
    generate_key_id,
    generate_master_key,
    generate_private_key,
)


class Grant(BaseModel):
    def __init__(
        self,
        key_id,
        name,
        grantee_principal,
        operations,
        constraints,
        retiring_principal,
    ):
        self.key_id = key_id
        self.name = name
        self.grantee_principal = grantee_principal
        self.retiring_principal = retiring_principal
        self.operations = operations
        self.constraints = constraints
        self.id = mock_random.get_random_hex()
        self.token = mock_random.get_random_hex()

    def to_json(self):
        return {
            "KeyId": self.key_id,
            "GrantId": self.id,
            "Name": self.name,
            "GranteePrincipal": self.grantee_principal,
            "RetiringPrincipal": self.retiring_principal,
            "Operations": self.operations,
            "Constraints": self.constraints,
        }


class Key(CloudFormationModel):
    def __init__(
        self,
        policy,
        key_usage,
        key_spec,
        description,
        account_id,
        region,
        multi_region=False,
    ):
        self.id = generate_key_id(multi_region)
        self.creation_date = unix_time()
        self.account_id = account_id
        self.policy = policy or self.generate_default_policy()
        self.key_usage = key_usage
        self.key_state = "Enabled"
        self.description = description or ""
        self.enabled = True
        self.region = region
        self.multi_region = multi_region
        self.key_rotation_status = False
        self.deletion_date = None
        self.key_material = generate_master_key()
        self.private_key = generate_private_key()
        self.origin = "AWS_KMS"
        self.key_manager = "CUSTOMER"
        self.key_spec = key_spec or "SYMMETRIC_DEFAULT"
        self.arn = f"arn:aws:kms:{region}:{account_id}:key/{self.id}"

        self.grants = dict()

    def add_grant(
        self, name, grantee_principal, operations, constraints, retiring_principal
    ) -> Grant:
        grant = Grant(
            self.id,
            name,
            grantee_principal,
            operations,
            constraints=constraints,
            retiring_principal=retiring_principal,
        )
        self.grants[grant.id] = grant
        return grant

    def list_grants(self, grant_id) -> [Grant]:
        grant_ids = [grant_id] if grant_id else self.grants.keys()
        return [grant for _id, grant in self.grants.items() if _id in grant_ids]

    def list_retirable_grants(self, retiring_principal) -> [Grant]:
        return [
            grant
            for grant in self.grants.values()
            if grant.retiring_principal == retiring_principal
        ]

    def revoke_grant(self, grant_id) -> None:
        if not self.grants.pop(grant_id, None):
            raise JsonRESTError("NotFoundException", f"Grant ID {grant_id} not found")

    def retire_grant(self, grant_id) -> None:
        self.grants.pop(grant_id, None)

    def retire_grant_by_token(self, grant_token) -> None:
        self.grants = {
            _id: grant
            for _id, grant in self.grants.items()
            if grant.token != grant_token
        }

    def generate_default_policy(self):
        return json.dumps(
            {
                "Version": "2012-10-17",
                "Id": "key-default-1",
                "Statement": [
                    {
                        "Sid": "Enable IAM User Permissions",
                        "Effect": "Allow",
                        "Principal": {"AWS": f"arn:aws:iam::{self.account_id}:root"},
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
    def encryption_algorithms(self):
        if self.key_usage == "SIGN_VERIFY":
            return None
        elif self.key_spec == "SYMMETRIC_DEFAULT":
            return ["SYMMETRIC_DEFAULT"]
        else:
            return ["RSAES_OAEP_SHA_1", "RSAES_OAEP_SHA_256"]

    @property
    def signing_algorithms(self):
        if self.key_usage == "ENCRYPT_DECRYPT":
            return None
        elif self.key_spec in ["ECC_NIST_P256", "ECC_SECG_P256K1"]:
            return ["ECDSA_SHA_256"]
        elif self.key_spec == "ECC_NIST_P384":
            return ["ECDSA_SHA_384"]
        elif self.key_spec == "ECC_NIST_P521":
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
                "CustomerMasterKeySpec": self.key_spec,
                "KeySpec": self.key_spec,
                "Description": self.description,
                "Enabled": self.enabled,
                "EncryptionAlgorithms": self.encryption_algorithms,
                "KeyId": self.id,
                "KeyManager": self.key_manager,
                "KeyUsage": self.key_usage,
                "KeyState": self.key_state,
                "MultiRegion": self.multi_region,
                "Origin": self.origin,
                "SigningAlgorithms": self.signing_algorithms,
            }
        }
        if self.key_state == "PendingDeletion":
            key_dict["KeyMetadata"]["DeletionDate"] = unix_time(self.deletion_date)
        return key_dict

    def delete(self, account_id, region_name):
        kms_backends[account_id][region_name].delete_key(self.id)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-kms-key.html
        return "AWS::KMS::Key"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        kms_backend = kms_backends[account_id][region_name]
        properties = cloudformation_json["Properties"]

        key = kms_backend.create_key(
            policy=properties["KeyPolicy"],
            key_usage="ENCRYPT_DECRYPT",
            key_spec="SYMMETRIC_DEFAULT",
            description=properties["Description"],
            tags=properties.get("Tags", []),
        )
        key.key_rotation_status = properties["EnableKeyRotation"]
        key.enabled = properties["Enabled"]

        return key

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["Arn"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Arn":
            return self.arn
        raise UnformattedGetAttTemplateException()


class KmsBackend(BaseBackend):
    def __init__(self, region_name, account_id=None):
        super().__init__(region_name=region_name, account_id=account_id)
        self.keys = {}
        self.key_to_aliases = defaultdict(set)
        self.tagger = TaggingService(key_name="TagKey", value_name="TagValue")

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "kms"
        )

    def _generate_default_keys(self, alias_name):
        """Creates default kms keys"""
        if alias_name in RESERVED_ALIASES:
            key = self.create_key(
                None,
                "ENCRYPT_DECRYPT",
                "SYMMETRIC_DEFAULT",
                "Default key",
                None,
            )
            self.add_alias(key.id, alias_name)
            return key.id

    def create_key(
        self, policy, key_usage, key_spec, description, tags, multi_region=False
    ):
        key = Key(
            policy,
            key_usage,
            key_spec,
            description,
            self.account_id,
            self.region_name,
            multi_region,
        )
        self.keys[key.id] = key
        if tags is not None and len(tags) > 0:
            self.tag_resource(key.id, tags)
        return key

    # https://docs.aws.amazon.com/kms/latest/developerguide/multi-region-keys-overview.html#mrk-sync-properties
    # In AWS replicas of a key only share some properties with the original key. Some of those properties get updated
    # in all replicas automatically if those properties change in the original key. Also, such properties can not be
    # changed for replicas directly.
    #
    # In our implementation with just create a copy of all the properties once without any protection from change,
    # as the exact implementation is currently infeasible.
    def replicate_key(self, key_id, replica_region):
        # Using copy() instead of deepcopy(), as the latter results in exception:
        #    TypeError: cannot pickle '_cffi_backend.FFI' object
        # Since we only update top level properties, copy() should suffice.
        replica_key = copy(self.keys[key_id])
        replica_key.region = replica_region
        to_region_backend = kms_backends[self.account_id][replica_region]
        to_region_backend.keys[replica_key.id] = replica_key

    def update_key_description(self, key_id, description):
        key = self.keys[self.get_key_id(key_id)]
        key.description = description

    def delete_key(self, key_id):
        if key_id in self.keys:
            if key_id in self.key_to_aliases:
                self.key_to_aliases.pop(key_id)
            self.tagger.delete_all_tags_for_resource(key_id)

            return self.keys.pop(key_id)

    def describe_key(self, key_id) -> Key:
        # allow the different methods (alias, ARN :key/, keyId, ARN alias) to
        # describe key not just KeyId
        key_id = self.get_key_id(key_id)
        if r"alias/" in str(key_id).lower():
            key_id = self.get_key_id_from_alias(key_id)
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
            return "alias/" + alias_name.split(":alias/")[1]

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
        if alias_name in RESERVED_ALIASES:
            key_id = self._generate_default_keys(alias_name)
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

    def generate_data_key(self, key_id, encryption_context, number_of_bytes, key_spec):
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

    def create_grant(
        self,
        key_id,
        grantee_principal,
        operations,
        name,
        constraints,
        retiring_principal,
    ):
        key = self.describe_key(key_id)
        grant = key.add_grant(
            name,
            grantee_principal,
            operations,
            constraints=constraints,
            retiring_principal=retiring_principal,
        )
        return grant.id, grant.token

    def list_grants(self, key_id, grant_id) -> [Grant]:
        key = self.describe_key(key_id)
        return key.list_grants(grant_id)

    def list_retirable_grants(self, retiring_principal):
        grants = []
        for key in self.keys.values():
            grants.extend(key.list_retirable_grants(retiring_principal))
        return grants

    def revoke_grant(self, key_id, grant_id) -> None:
        key = self.describe_key(key_id)
        key.revoke_grant(grant_id)

    def retire_grant(self, key_id, grant_id, grant_token) -> None:
        if grant_token:
            for key in self.keys.values():
                key.retire_grant_by_token(grant_token)
        else:
            key = self.describe_key(key_id)
            key.retire_grant(grant_id)

    def __ensure_valid_sign_and_verify_key(self, key: Key):
        if key.key_usage != "SIGN_VERIFY":
            raise ValidationException(
                (
                    "1 validation error detected: Value '{key_id}' at 'KeyId' failed "
                    "to satisfy constraint: Member must point to a key with usage: 'SIGN_VERIFY'"
                ).format(key_id=key.id)
            )

    def __ensure_valid_signing_augorithm(self, key: Key, signing_algorithm):
        if signing_algorithm not in key.signing_algorithms:
            raise ValidationException(
                (
                    "1 validation error detected: Value '{signing_algorithm}' at 'SigningAlgorithm' failed "
                    "to satisfy constraint: Member must satisfy enum value set: "
                    "{valid_sign_algorithms}"
                ).format(
                    signing_algorithm=signing_algorithm,
                    valid_sign_algorithms=key.signing_algorithms,
                )
            )

    def sign(self, key_id, message, signing_algorithm):
        """Sign message using generated private key.

        - signing_algorithm is ignored and hardcoded to RSASSA_PSS_SHA_256

        - grant_tokens are not implemented
        """
        key = self.describe_key(key_id)

        self.__ensure_valid_sign_and_verify_key(key)
        self.__ensure_valid_signing_augorithm(key, signing_algorithm)

        # TODO: support more than one hardcoded algorithm based on KeySpec
        signature = key.private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )

        return key.arn, signature, signing_algorithm

    def verify(self, key_id, message, signature, signing_algorithm):
        """Verify message using public key from generated private key.

        - signing_algorithm is ignored and hardcoded to RSASSA_PSS_SHA_256

        - grant_tokens are not implemented
        """
        key = self.describe_key(key_id)

        self.__ensure_valid_sign_and_verify_key(key)
        self.__ensure_valid_signing_augorithm(key, signing_algorithm)

        if signing_algorithm not in key.signing_algorithms:
            raise ValidationException(
                (
                    "1 validation error detected: Value '{signing_algorithm}' at 'SigningAlgorithm' failed "
                    "to satisfy constraint: Member must satisfy enum value set: "
                    "{valid_sign_algorithms}"
                ).format(
                    signing_algorithm=signing_algorithm,
                    valid_sign_algorithms=key.signing_algorithms,
                )
            )

        public_key = key.private_key.public_key()

        try:
            # TODO: support more than one hardcoded algorithm based on KeySpec
            public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return key.arn, True, signing_algorithm
        except InvalidSignature:
            return key.arn, False, signing_algorithm


kms_backends = BackendDict(KmsBackend, "kms")
