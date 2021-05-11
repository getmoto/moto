# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time
import json
import uuid
import datetime

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from .exceptions import (
    SecretNotFoundException,
    SecretHasNoValueException,
    InvalidParameterException,
    ResourceExistsException,
    ResourceNotFoundException,
    InvalidRequestException,
    ClientError,
)
from .utils import random_password, secret_arn, get_secret_name_from_arn
from .list_secrets.filters import all, tag_key, tag_value, description, name


_filter_functions = {
    "all": all,
    "name": name,
    "description": description,
    "tag-key": tag_key,
    "tag-value": tag_value,
}


def filter_keys():
    return list(_filter_functions.keys())


def _matches(secret, filters):
    is_match = True

    for f in filters:
        # Filter names are pre-validated in the resource layer
        filter_function = _filter_functions.get(f["Key"])
        is_match = is_match and filter_function(secret, f["Values"])

    return is_match


class SecretsManager(BaseModel):
    def __init__(self, region_name, **kwargs):
        self.region = region_name


class FakeSecret:
    def __init__(
        self,
        region_name,
        secret_id,
        secret_string=None,
        secret_binary=None,
        description=None,
        tags=[],
        version_id=None,
        version_stages=None,
    ):
        self.secret_id = secret_id
        self.name = secret_id
        self.arn = secret_arn(region_name, secret_id)
        self.secret_string = secret_string
        self.secret_binary = secret_binary
        self.description = description
        self.tags = tags
        self.version_id = version_id
        self.version_stages = version_stages
        self.rotation_enabled = False
        self.rotation_lambda_arn = ""
        self.auto_rotate_after_days = 0
        self.deleted_date = None

    def update(self, description=None, tags=[]):
        self.description = description
        self.tags = tags

    def set_versions(self, versions):
        self.versions = versions

    def set_default_version_id(self, version_id):
        self.default_version_id = version_id

    def reset_default_version(self, secret_version, version_id):
        # remove all old AWSPREVIOUS stages
        for old_version in self.versions.values():
            if "AWSPREVIOUS" in old_version["version_stages"]:
                old_version["version_stages"].remove("AWSPREVIOUS")

        # set old AWSCURRENT secret to AWSPREVIOUS
        previous_current_version_id = self.default_version_id
        self.versions[previous_current_version_id]["version_stages"] = ["AWSPREVIOUS"]

        self.versions[version_id] = secret_version
        self.default_version_id = version_id

    def delete(self, deleted_date):
        self.deleted_date = deleted_date

    def restore(self):
        self.deleted_date = None

    def is_deleted(self):
        return self.deleted_date is not None

    def to_short_dict(self, include_version_stages=False):
        dct = {
            "ARN": self.arn,
            "Name": self.name,
            "VersionId": self.default_version_id,
        }
        if include_version_stages:
            dct["VersionStages"] = self.version_stages
        return json.dumps(dct)

    def to_dict(self):
        version_id_to_stages = self._form_version_ids_to_stages()

        return {
            "ARN": self.arn,
            "Name": self.name,
            "Description": self.description or "",
            "KmsKeyId": "",
            "RotationEnabled": self.rotation_enabled,
            "RotationLambdaARN": self.rotation_lambda_arn,
            "RotationRules": {"AutomaticallyAfterDays": self.auto_rotate_after_days},
            "LastRotatedDate": None,
            "LastChangedDate": None,
            "LastAccessedDate": None,
            "DeletedDate": self.deleted_date,
            "Tags": self.tags,
            "VersionIdsToStages": version_id_to_stages,
            "SecretVersionsToStages": version_id_to_stages,
        }

    def _form_version_ids_to_stages(self):
        version_id_to_stages = {}
        for key, value in self.versions.items():
            version_id_to_stages[key] = value["version_stages"]

        return version_id_to_stages


class SecretsStore(dict):
    def __setitem__(self, key, value):
        new_key = get_secret_name_from_arn(key)
        super(SecretsStore, self).__setitem__(new_key, value)

    def __getitem__(self, key):
        new_key = get_secret_name_from_arn(key)
        return super(SecretsStore, self).__getitem__(new_key)

    def __contains__(self, key):
        new_key = get_secret_name_from_arn(key)
        return dict.__contains__(self, new_key)

    def pop(self, key, *args, **kwargs):
        new_key = get_secret_name_from_arn(key)
        return super(SecretsStore, self).pop(new_key, *args, **kwargs)


class SecretsManagerBackend(BaseBackend):
    def __init__(self, region_name=None, **kwargs):
        super(SecretsManagerBackend, self).__init__()
        self.region = region_name
        self.secrets = SecretsStore()

    def reset(self):
        region_name = self.region
        self.__dict__ = {}
        self.__init__(region_name)

    def _is_valid_identifier(self, identifier):
        return identifier in self.secrets

    def _unix_time_secs(self, dt):
        epoch = datetime.datetime.utcfromtimestamp(0)
        return (dt - epoch).total_seconds()

    def get_secret_value(self, secret_id, version_id, version_stage):
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        if not version_id and version_stage:
            # set version_id to match version_stage
            versions_dict = self.secrets[secret_id].versions
            for ver_id, ver_val in versions_dict.items():
                if version_stage in ver_val["version_stages"]:
                    version_id = ver_id
                    break
            if not version_id:
                raise SecretNotFoundException()

        # TODO check this part
        if self.secrets[secret_id].is_deleted():
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the GetSecretValue operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

        secret = self.secrets[secret_id]
        version_id = version_id or secret.default_version_id

        secret_version = secret.versions.get(version_id)
        if not secret_version:
            raise ResourceNotFoundException(
                "An error occurred (ResourceNotFoundException) when calling the GetSecretValue operation: Secrets "
                "Manager can't find the specified secret value for VersionId: {}".format(
                    version_id
                )
            )

        response_data = {
            "ARN": secret.arn,
            "Name": secret.name,
            "VersionId": secret_version["version_id"],
            "VersionStages": secret_version["version_stages"],
            "CreatedDate": secret_version["createdate"],
        }

        if "secret_string" in secret_version:
            response_data["SecretString"] = secret_version["secret_string"]

        if "secret_binary" in secret_version:
            response_data["SecretBinary"] = secret_version["secret_binary"]

        if (
            "secret_string" not in secret_version
            and "secret_binary" not in secret_version
        ):
            raise SecretHasNoValueException(version_stage or "AWSCURRENT")

        response = json.dumps(response_data)

        return response

    def update_secret(
        self, secret_id, secret_string=None, secret_binary=None, **kwargs
    ):

        # error if secret does not exist
        if secret_id not in self.secrets.keys():
            raise SecretNotFoundException()

        if self.secrets[secret_id].is_deleted():
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the UpdateSecret operation: "
                "You can't perform this operation on the secret because it was marked for deletion."
            )

        secret = self.secrets[secret_id]
        tags = secret.tags
        description = secret.description

        secret = self._add_secret(
            secret_id,
            secret_string=secret_string,
            secret_binary=secret_binary,
            description=description,
            tags=tags,
        )

        return secret.to_short_dict()

    def create_secret(
        self, name, secret_string=None, secret_binary=None, description=None, tags=[]
    ):

        # error if secret exists
        if name in self.secrets.keys():
            raise ResourceExistsException(
                "A resource with the ID you requested already exists."
            )

        secret = self._add_secret(
            name,
            secret_string=secret_string,
            secret_binary=secret_binary,
            description=description,
            tags=tags,
        )

        return secret.to_short_dict()

    def _add_secret(
        self,
        secret_id,
        secret_string=None,
        secret_binary=None,
        description=None,
        tags=[],
        version_id=None,
        version_stages=None,
    ):

        if version_stages is None:
            version_stages = ["AWSCURRENT"]

        if not version_id:
            version_id = str(uuid.uuid4())

        secret_version = {
            "createdate": int(time.time()),
            "version_id": version_id,
            "version_stages": version_stages,
        }
        if secret_string is not None:
            secret_version["secret_string"] = secret_string

        if secret_binary is not None:
            secret_version["secret_binary"] = secret_binary

        if secret_id in self.secrets:
            secret = self.secrets[secret_id]
            secret.update(description, tags)

            if "AWSPENDING" in version_stages:
                secret.versions[version_id] = secret_version
            else:
                secret.reset_default_version(secret_version, version_id)
        else:
            secret = FakeSecret(
                region_name=self.region,
                secret_id=secret_id,
                secret_string=secret_string,
                secret_binary=secret_binary,
                description=description,
                tags=tags,
            )
            secret.set_versions({version_id: secret_version})
            secret.set_default_version_id(version_id)
            self.secrets[secret_id] = secret

        return secret

    def put_secret_value(
        self,
        secret_id,
        secret_string,
        secret_binary,
        client_request_token,
        version_stages,
    ):

        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()
        else:
            secret = self.secrets[secret_id]
            tags = secret.tags
            description = secret.description

        secret = self._add_secret(
            secret_id,
            secret_string,
            secret_binary,
            version_id=client_request_token,
            description=description,
            tags=tags,
            version_stages=version_stages,
        )

        return secret.to_short_dict(include_version_stages=True)

    def describe_secret(self, secret_id):
        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]

        return json.dumps(secret.to_dict())

    def rotate_secret(
        self,
        secret_id,
        client_request_token=None,
        rotation_lambda_arn=None,
        rotation_rules=None,
    ):

        rotation_days = "AutomaticallyAfterDays"

        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        if self.secrets[secret_id].is_deleted():
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the RotateSecret operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

        if client_request_token:
            token_length = len(client_request_token)
            if token_length < 32 or token_length > 64:
                msg = "ClientRequestToken " "must be 32-64 characters long."
                raise InvalidParameterException(msg)

        if rotation_lambda_arn:
            if len(rotation_lambda_arn) > 2048:
                msg = "RotationLambdaARN " "must <= 2048 characters long."
                raise InvalidParameterException(msg)

        if rotation_rules:
            if rotation_days in rotation_rules:
                rotation_period = rotation_rules[rotation_days]
                if rotation_period < 1 or rotation_period > 1000:
                    msg = (
                        "RotationRules.AutomaticallyAfterDays " "must be within 1-1000."
                    )
                    raise InvalidParameterException(msg)

        secret = self.secrets[secret_id]

        # The rotation function must end with the versions of the secret in
        # one of two states:
        #
        #  - The AWSPENDING and AWSCURRENT staging labels are attached to the
        #    same version of the secret, or
        #  - The AWSPENDING staging label is not attached to any version of the secret.
        #
        # If the AWSPENDING staging label is present but not attached to the same
        # version as AWSCURRENT then any later invocation of RotateSecret assumes
        # that a previous rotation request is still in progress and returns an error.
        try:
            version = next(
                version
                for version in secret.versions.values()
                if "AWSPENDING" in version["version_stages"]
            )
            if "AWSCURRENT" in version["version_stages"]:
                msg = "Previous rotation request is still in progress."
                raise InvalidRequestException(msg)

        except StopIteration:
            # Pending is not present in any version
            pass

        old_secret_version = secret.versions[secret.default_version_id]
        new_version_id = client_request_token or str(uuid.uuid4())

        # We add the new secret version as "pending". The previous version remains
        # as "current" for now. Once we've passed the new secret through the lambda
        # rotation function (if provided) we can then update the status to "current".
        self._add_secret(
            secret_id,
            old_secret_version["secret_string"],
            description=secret.description,
            tags=secret.tags,
            version_id=new_version_id,
            version_stages=["AWSPENDING"],
        )
        secret.rotation_lambda_arn = rotation_lambda_arn or ""
        if rotation_rules:
            secret.auto_rotate_after_days = rotation_rules.get(rotation_days, 0)
        if secret.auto_rotate_after_days > 0:
            secret.rotation_enabled = True

        # Begin the rotation process for the given secret by invoking the lambda function.
        if secret.rotation_lambda_arn:
            from moto.awslambda.models import lambda_backends

            lambda_backend = lambda_backends[self.region]

            request_headers = {}
            response_headers = {}

            func = lambda_backend.get_function(secret.rotation_lambda_arn)
            if not func:
                msg = "Resource not found for ARN '{}'.".format(
                    secret.rotation_lambda_arn
                )
                raise ResourceNotFoundException(msg)

            for step in ["create", "set", "test", "finish"]:
                func.invoke(
                    json.dumps(
                        {
                            "Step": step + "Secret",
                            "SecretId": secret.name,
                            "ClientRequestToken": new_version_id,
                        }
                    ),
                    request_headers,
                    response_headers,
                )

            secret.set_default_version_id(new_version_id)
        else:
            secret.reset_default_version(
                secret.versions[new_version_id], new_version_id
            )
            secret.versions[new_version_id]["version_stages"] = ["AWSCURRENT"]

        return secret.to_short_dict()

    def get_random_password(
        self,
        password_length,
        exclude_characters,
        exclude_numbers,
        exclude_punctuation,
        exclude_uppercase,
        exclude_lowercase,
        include_space,
        require_each_included_type,
    ):
        # password size must have value less than or equal to 4096
        if password_length > 4096:
            raise ClientError(
                "ClientError: An error occurred (ValidationException) \
                when calling the GetRandomPassword operation: 1 validation error detected: Value '{}' at 'passwordLength' \
                failed to satisfy constraint: Member must have value less than or equal to 4096".format(
                    password_length
                )
            )
        if password_length < 4:
            raise InvalidParameterException(
                "InvalidParameterException: An error occurred (InvalidParameterException) \
                when calling the GetRandomPassword operation: Password length is too short based on the required types."
            )

        response = json.dumps(
            {
                "RandomPassword": random_password(
                    password_length,
                    exclude_characters,
                    exclude_numbers,
                    exclude_punctuation,
                    exclude_uppercase,
                    exclude_lowercase,
                    include_space,
                    require_each_included_type,
                )
            }
        )

        return response

    def list_secret_version_ids(self, secret_id):
        secret = self.secrets[secret_id]

        version_list = []
        for version_id, version in secret.versions.items():
            version_list.append(
                {
                    "CreatedDate": int(time.time()),
                    "LastAccessedDate": int(time.time()),
                    "VersionId": version_id,
                    "VersionStages": version["version_stages"],
                }
            )

        response = json.dumps(
            {
                "ARN": secret.secret_id,
                "Name": secret.name,
                "NextToken": "",
                "Versions": version_list,
            }
        )

        return response

    def list_secrets(self, filters, max_results, next_token):
        # TODO implement pagination and limits

        secret_list = []
        for secret in self.secrets.values():
            if _matches(secret, filters):
                secret_list.append(secret.to_dict())

        return secret_list, None

    def delete_secret(
        self, secret_id, recovery_window_in_days, force_delete_without_recovery
    ):

        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        if self.secrets[secret_id].is_deleted():
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the DeleteSecret operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

        if recovery_window_in_days and force_delete_without_recovery:
            raise InvalidParameterException(
                "An error occurred (InvalidParameterException) when calling the DeleteSecret operation: You can't \
                use ForceDeleteWithoutRecovery in conjunction with RecoveryWindowInDays."
            )

        if recovery_window_in_days and (
            recovery_window_in_days < 7 or recovery_window_in_days > 30
        ):
            raise InvalidParameterException(
                "An error occurred (InvalidParameterException) when calling the DeleteSecret operation: The \
                RecoveryWindowInDays value must be between 7 and 30 days (inclusive)."
            )

        deletion_date = datetime.datetime.utcnow()

        if force_delete_without_recovery:
            secret = self.secrets.pop(secret_id, None)
        else:
            deletion_date += datetime.timedelta(days=recovery_window_in_days or 30)
            self.secrets[secret_id].delete(self._unix_time_secs(deletion_date))
            secret = self.secrets.get(secret_id, None)

        if not secret:
            raise SecretNotFoundException()

        arn = secret.arn
        name = secret.name

        return arn, name, self._unix_time_secs(deletion_date)

    def restore_secret(self, secret_id):

        if not self._is_valid_identifier(secret_id):
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        secret.restore()

        return secret.arn, secret.name

    def tag_resource(self, secret_id, tags):

        if secret_id not in self.secrets.keys():
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        old_tags = secret.tags

        for tag in tags:
            old_tags.append(tag)

        return secret_id

    def untag_resource(self, secret_id, tag_keys):

        if secret_id not in self.secrets.keys():
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]
        tags = secret.tags

        for tag in tags:
            if tag["Key"] in tag_keys:
                tags.remove(tag)

        return secret_id

    def update_secret_version_stage(
        self, secret_id, version_stage, remove_from_version_id, move_to_version_id
    ):
        if secret_id not in self.secrets.keys():
            raise SecretNotFoundException()

        secret = self.secrets[secret_id]

        if remove_from_version_id:
            if remove_from_version_id not in secret.versions:
                raise InvalidParameterException(
                    "Not a valid version: %s" % remove_from_version_id
                )

            stages = secret.versions[remove_from_version_id]["version_stages"]
            if version_stage not in stages:
                raise InvalidParameterException(
                    "Version stage %s not found in version %s"
                    % (version_stage, remove_from_version_id)
                )

            stages.remove(version_stage)

        if move_to_version_id:
            if move_to_version_id not in secret.versions:
                raise InvalidParameterException(
                    "Not a valid version: %s" % move_to_version_id
                )

            stages = secret.versions[move_to_version_id]["version_stages"]
            stages.append(version_stage)

        if version_stage == "AWSCURRENT":
            if remove_from_version_id:
                # Whenever you move AWSCURRENT, Secrets Manager automatically
                # moves the label AWSPREVIOUS to the version that AWSCURRENT
                # was removed from.
                secret.versions[remove_from_version_id]["version_stages"].append(
                    "AWSPREVIOUS"
                )

            if move_to_version_id:
                stages = secret.versions[move_to_version_id]["version_stages"]
                if "AWSPREVIOUS" in stages:
                    stages.remove("AWSPREVIOUS")

        return secret_id

    @staticmethod
    def get_resource_policy(secret_id):
        resource_policy = {
            "Version": "2012-10-17",
            "Statement": {
                "Effect": "Allow",
                "Principal": {
                    "AWS": [
                        "arn:aws:iam::111122223333:root",
                        "arn:aws:iam::444455556666:root",
                    ]
                },
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": "*",
            },
        }
        return json.dumps(
            {
                "ARN": secret_id,
                "Name": secret_id,
                "ResourcePolicy": json.dumps(resource_policy),
            }
        )


secretsmanager_backends = {}
for region in Session().get_available_regions("secretsmanager"):
    secretsmanager_backends[region] = SecretsManagerBackend(region_name=region)
for region in Session().get_available_regions(
    "secretsmanager", partition_name="aws-us-gov"
):
    secretsmanager_backends[region] = SecretsManagerBackend(region_name=region)
for region in Session().get_available_regions(
    "secretsmanager", partition_name="aws-cn"
):
    secretsmanager_backends[region] = SecretsManagerBackend(region_name=region)
