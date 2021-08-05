from __future__ import unicode_literals

import base64
import json
import os
import re

from moto.core.responses import BaseResponse
from .models import kms_backends
from .exceptions import (
    NotFoundException,
    ValidationException,
    AlreadyExistsException,
    NotAuthorizedException,
)

ACCOUNT_ID = "012345678912"
reserved_aliases = [
    "alias/aws/ebs",
    "alias/aws/s3",
    "alias/aws/redshift",
    "alias/aws/rds",
]


class KmsResponse(BaseResponse):
    @property
    def parameters(self):
        params = json.loads(self.body)

        for key in ("Plaintext", "CiphertextBlob"):
            if key in params:
                params[key] = base64.b64decode(params[key].encode("utf-8"))

        return params

    @property
    def kms_backend(self):
        return kms_backends[self.region]

    def _display_arn(self, key_id):
        if key_id.startswith("arn:"):
            return key_id

        if key_id.startswith("alias/"):
            id_type = ""
        else:
            id_type = "key/"

        return "arn:aws:kms:{region}:{account}:{id_type}{key_id}".format(
            region=self.region, account=ACCOUNT_ID, id_type=id_type, key_id=key_id
        )

    def _validate_cmk_id(self, key_id):
        """Determine whether a CMK ID exists.

        - raw key ID
        - key ARN
        """
        is_arn = key_id.startswith("arn:") and ":key/" in key_id
        is_raw_key_id = re.match(
            r"^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$",
            key_id,
            re.IGNORECASE,
        )

        if not is_arn and not is_raw_key_id:
            raise NotFoundException("Invalid keyId {key_id}".format(key_id=key_id))

        cmk_id = self.kms_backend.get_key_id(key_id)

        if cmk_id not in self.kms_backend.keys:
            raise NotFoundException(
                "Key '{key_id}' does not exist".format(key_id=self._display_arn(key_id))
            )

    def _validate_alias(self, key_id):
        """Determine whether an alias exists.

        - alias name
        - alias ARN
        """
        error = NotFoundException(
            "Alias {key_id} is not found.".format(key_id=self._display_arn(key_id))
        )

        is_arn = key_id.startswith("arn:") and ":alias/" in key_id
        is_name = key_id.startswith("alias/")

        if not is_arn and not is_name:
            raise error

        alias_name = self.kms_backend.get_alias_name(key_id)
        cmk_id = self.kms_backend.get_key_id_from_alias(alias_name)
        if cmk_id is None:
            raise error

    def _validate_key_id(self, key_id):
        """Determine whether or not a key ID exists.

        - raw key ID
        - key ARN
        - alias name
        - alias ARN
        """
        is_alias_arn = key_id.startswith("arn:") and ":alias/" in key_id
        is_alias_name = key_id.startswith("alias/")

        if is_alias_arn or is_alias_name:
            self._validate_alias(key_id)
            return

        self._validate_cmk_id(key_id)

    def create_key(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateKey.html"""
        policy = self.parameters.get("Policy")
        key_usage = self.parameters.get("KeyUsage")
        customer_master_key_spec = self.parameters.get("CustomerMasterKeySpec")
        description = self.parameters.get("Description")
        tags = self.parameters.get("Tags")

        key = self.kms_backend.create_key(
            policy, key_usage, customer_master_key_spec, description, tags, self.region
        )
        return json.dumps(key.to_dict())

    def update_key_description(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_UpdateKeyDescription.html"""
        key_id = self.parameters.get("KeyId")
        description = self.parameters.get("Description")

        self._validate_cmk_id(key_id)

        self.kms_backend.update_key_description(key_id, description)
        return json.dumps(None)

    def tag_resource(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_TagResource.html"""
        key_id = self.parameters.get("KeyId")
        tags = self.parameters.get("Tags")

        self._validate_cmk_id(key_id)

        result = self.kms_backend.tag_resource(key_id, tags)
        return json.dumps(result)

    def untag_resource(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_UntagResource.html"""
        key_id = self.parameters.get("KeyId")
        tag_names = self.parameters.get("TagKeys")

        self._validate_cmk_id(key_id)

        result = self.kms_backend.untag_resource(key_id, tag_names)
        return json.dumps(result)

    def list_resource_tags(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_ListResourceTags.html"""
        key_id = self.parameters.get("KeyId")
        self._validate_cmk_id(key_id)

        tags = self.kms_backend.list_resource_tags(key_id)
        tags.update({"NextMarker": None, "Truncated": False})
        return json.dumps(tags)

    def describe_key(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_DescribeKey.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_key_id(key_id)

        key = self.kms_backend.describe_key(self.kms_backend.get_key_id(key_id))

        return json.dumps(key.to_dict())

    def list_keys(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_ListKeys.html"""
        keys = self.kms_backend.list_keys()

        return json.dumps(
            {
                "Keys": [{"KeyArn": key.arn, "KeyId": key.id} for key in keys],
                "NextMarker": None,
                "Truncated": False,
            }
        )

    def create_alias(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_CreateAlias.html"""
        return self._set_alias()

    def update_alias(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_UpdateAlias.html"""
        return self._set_alias(update=True)

    def _set_alias(self, update=False):
        alias_name = self.parameters["AliasName"]
        target_key_id = self.parameters["TargetKeyId"]

        if not alias_name.startswith("alias/"):
            raise ValidationException("Invalid identifier")

        if alias_name in reserved_aliases:
            raise NotAuthorizedException()

        if ":" in alias_name:
            raise ValidationException(
                "{alias_name} contains invalid characters for an alias".format(
                    alias_name=alias_name
                )
            )

        if not re.match(r"^[a-zA-Z0-9:/_-]+$", alias_name):
            raise ValidationException(
                "1 validation error detected: Value '{alias_name}' at 'aliasName' "
                "failed to satisfy constraint: Member must satisfy regular "
                "expression pattern: ^[a-zA-Z0-9:/_-]+$".format(alias_name=alias_name)
            )

        if self.kms_backend.alias_exists(target_key_id):
            raise ValidationException("Aliases must refer to keys. Not aliases")

        if update:
            # delete any existing aliases with that name (should be a no-op if none exist)
            self.kms_backend.delete_alias(alias_name)

        if self.kms_backend.alias_exists(alias_name):
            raise AlreadyExistsException(
                "An alias with the name arn:aws:kms:{region}:012345678912:{alias_name} "
                "already exists".format(region=self.region, alias_name=alias_name)
            )

        self._validate_cmk_id(target_key_id)

        self.kms_backend.add_alias(target_key_id, alias_name)

        return json.dumps({})

    def delete_alias(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_DeleteAlias.html"""
        alias_name = self.parameters["AliasName"]

        if not alias_name.startswith("alias/"):
            raise ValidationException("Invalid identifier")

        self._validate_alias(alias_name)

        self.kms_backend.delete_alias(alias_name)

        return json.dumps(None)

    def list_aliases(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_ListAliases.html"""
        region = self.region

        # TODO: The actual API can filter on KeyId.

        response_aliases = [
            {
                "AliasArn": "arn:aws:kms:{region}:012345678912:{reserved_alias}".format(
                    region=region, reserved_alias=reserved_alias
                ),
                "AliasName": reserved_alias,
            }
            for reserved_alias in reserved_aliases
        ]

        backend_aliases = self.kms_backend.get_all_aliases()
        for target_key_id, aliases in backend_aliases.items():
            for alias_name in aliases:
                response_aliases.append(
                    {
                        "AliasArn": "arn:aws:kms:{region}:012345678912:{alias_name}".format(
                            region=region, alias_name=alias_name
                        ),
                        "AliasName": alias_name,
                        "TargetKeyId": target_key_id,
                    }
                )

        return json.dumps({"Truncated": False, "Aliases": response_aliases})

    def enable_key_rotation(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_EnableKeyRotation.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_cmk_id(key_id)

        self.kms_backend.enable_key_rotation(key_id)

        return json.dumps(None)

    def disable_key_rotation(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_EnableKeyRotation.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_cmk_id(key_id)

        self.kms_backend.disable_key_rotation(key_id)

        return json.dumps(None)

    def get_key_rotation_status(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_GetKeyRotationStatus.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_cmk_id(key_id)

        rotation_enabled = self.kms_backend.get_key_rotation_status(key_id)

        return json.dumps({"KeyRotationEnabled": rotation_enabled})

    def put_key_policy(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_PutKeyPolicy.html"""
        key_id = self.parameters.get("KeyId")
        policy_name = self.parameters.get("PolicyName")
        policy = self.parameters.get("Policy")
        _assert_default_policy(policy_name)

        self._validate_cmk_id(key_id)

        self.kms_backend.put_key_policy(key_id, policy)

        return json.dumps(None)

    def get_key_policy(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_GetKeyPolicy.html"""
        key_id = self.parameters.get("KeyId")
        policy_name = self.parameters.get("PolicyName")
        _assert_default_policy(policy_name)

        self._validate_cmk_id(key_id)

        policy = self.kms_backend.get_key_policy(key_id) or "{}"
        return json.dumps({"Policy": policy})

    def list_key_policies(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_ListKeyPolicies.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_cmk_id(key_id)

        self.kms_backend.describe_key(key_id)

        return json.dumps({"Truncated": False, "PolicyNames": ["default"]})

    def encrypt(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_Encrypt.html"""
        key_id = self.parameters.get("KeyId")
        encryption_context = self.parameters.get("EncryptionContext", {})
        plaintext = self.parameters.get("Plaintext")

        self._validate_key_id(key_id)

        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        ciphertext_blob, arn = self.kms_backend.encrypt(
            key_id=key_id, plaintext=plaintext, encryption_context=encryption_context
        )
        ciphertext_blob_response = base64.b64encode(ciphertext_blob).decode("utf-8")

        return json.dumps({"CiphertextBlob": ciphertext_blob_response, "KeyId": arn})

    def decrypt(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_Decrypt.html"""
        ciphertext_blob = self.parameters.get("CiphertextBlob")
        encryption_context = self.parameters.get("EncryptionContext", {})

        plaintext, arn = self.kms_backend.decrypt(
            ciphertext_blob=ciphertext_blob, encryption_context=encryption_context
        )

        plaintext_response = base64.b64encode(plaintext).decode("utf-8")

        return json.dumps({"Plaintext": plaintext_response, "KeyId": arn})

    def re_encrypt(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_ReEncrypt.html"""
        ciphertext_blob = self.parameters.get("CiphertextBlob")
        source_encryption_context = self.parameters.get("SourceEncryptionContext", {})
        destination_key_id = self.parameters.get("DestinationKeyId")
        destination_encryption_context = self.parameters.get(
            "DestinationEncryptionContext", {}
        )

        self._validate_cmk_id(destination_key_id)

        (
            new_ciphertext_blob,
            decrypting_arn,
            encrypting_arn,
        ) = self.kms_backend.re_encrypt(
            ciphertext_blob=ciphertext_blob,
            source_encryption_context=source_encryption_context,
            destination_key_id=destination_key_id,
            destination_encryption_context=destination_encryption_context,
        )

        response_ciphertext_blob = base64.b64encode(new_ciphertext_blob).decode("utf-8")

        return json.dumps(
            {
                "CiphertextBlob": response_ciphertext_blob,
                "KeyId": encrypting_arn,
                "SourceKeyId": decrypting_arn,
            }
        )

    def disable_key(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_DisableKey.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_cmk_id(key_id)

        self.kms_backend.disable_key(key_id)

        return json.dumps(None)

    def enable_key(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_EnableKey.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_cmk_id(key_id)

        self.kms_backend.enable_key(key_id)

        return json.dumps(None)

    def cancel_key_deletion(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_CancelKeyDeletion.html"""
        key_id = self.parameters.get("KeyId")

        self._validate_cmk_id(key_id)

        self.kms_backend.cancel_key_deletion(key_id)

        return json.dumps({"KeyId": key_id})

    def schedule_key_deletion(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_ScheduleKeyDeletion.html"""
        key_id = self.parameters.get("KeyId")
        if self.parameters.get("PendingWindowInDays") is None:
            pending_window_in_days = 30
        else:
            pending_window_in_days = self.parameters.get("PendingWindowInDays")

        self._validate_cmk_id(key_id)

        return json.dumps(
            {
                "KeyId": key_id,
                "DeletionDate": self.kms_backend.schedule_key_deletion(
                    key_id, pending_window_in_days
                ),
            }
        )

    def generate_data_key(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_GenerateDataKey.html"""
        key_id = self.parameters.get("KeyId")
        encryption_context = self.parameters.get("EncryptionContext", {})
        number_of_bytes = self.parameters.get("NumberOfBytes")
        key_spec = self.parameters.get("KeySpec")
        grant_tokens = self.parameters.get("GrantTokens")

        # Param validation
        self._validate_key_id(key_id)

        if number_of_bytes and (number_of_bytes > 1024 or number_of_bytes < 1):
            raise ValidationException(
                (
                    "1 validation error detected: Value '{number_of_bytes:d}' at 'numberOfBytes' failed "
                    "to satisfy constraint: Member must have value less than or "
                    "equal to 1024"
                ).format(number_of_bytes=number_of_bytes)
            )

        if key_spec and key_spec not in ("AES_256", "AES_128"):
            raise ValidationException(
                (
                    "1 validation error detected: Value '{key_spec}' at 'keySpec' failed "
                    "to satisfy constraint: Member must satisfy enum value set: "
                    "[AES_256, AES_128]"
                ).format(key_spec=key_spec)
            )
        if not key_spec and not number_of_bytes:
            raise ValidationException(
                "Please specify either number of bytes or key spec."
            )

        if key_spec and number_of_bytes:
            raise ValidationException(
                "Please specify either number of bytes or key spec."
            )

        plaintext, ciphertext_blob, key_arn = self.kms_backend.generate_data_key(
            key_id=key_id,
            encryption_context=encryption_context,
            number_of_bytes=number_of_bytes,
            key_spec=key_spec,
            grant_tokens=grant_tokens,
        )

        plaintext_response = base64.b64encode(plaintext).decode("utf-8")
        ciphertext_blob_response = base64.b64encode(ciphertext_blob).decode("utf-8")

        return json.dumps(
            {
                "CiphertextBlob": ciphertext_blob_response,
                "Plaintext": plaintext_response,
                "KeyId": key_arn,  # not alias
            }
        )

    def generate_data_key_without_plaintext(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_GenerateDataKeyWithoutPlaintext.html"""
        result = json.loads(self.generate_data_key())
        del result["Plaintext"]

        return json.dumps(result)

    def generate_random(self):
        """https://docs.aws.amazon.com/kms/latest/APIReference/API_GenerateRandom.html"""
        number_of_bytes = self.parameters.get("NumberOfBytes")

        if number_of_bytes and (number_of_bytes > 1024 or number_of_bytes < 1):
            raise ValidationException(
                (
                    "1 validation error detected: Value '{number_of_bytes:d}' at 'numberOfBytes' failed "
                    "to satisfy constraint: Member must have value less than or "
                    "equal to 1024"
                ).format(number_of_bytes=number_of_bytes)
            )

        entropy = os.urandom(number_of_bytes)

        response_entropy = base64.b64encode(entropy).decode("utf-8")

        return json.dumps({"Plaintext": response_entropy})


def _assert_default_policy(policy_name):
    if policy_name != "default":
        raise NotFoundException("No such policy exists")
