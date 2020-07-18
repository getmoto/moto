from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from moto.secretsmanager.exceptions import InvalidRequestException

from .models import secretsmanager_backends

import json


class SecretsManagerResponse(BaseResponse):
    def get_secret_value(self):
        secret_id = self._get_param("SecretId")
        version_id = self._get_param("VersionId")
        version_stage = self._get_param("VersionStage")
        return secretsmanager_backends[self.region].get_secret_value(
            secret_id=secret_id, version_id=version_id, version_stage=version_stage
        )

    def create_secret(self):
        name = self._get_param("Name")
        secret_string = self._get_param("SecretString")
        secret_binary = self._get_param("SecretBinary")
        description = self._get_param("Description", if_none="")
        tags = self._get_param("Tags", if_none=[])
        return secretsmanager_backends[self.region].create_secret(
            name=name,
            secret_string=secret_string,
            secret_binary=secret_binary,
            description=description,
            tags=tags,
        )

    def update_secret(self):
        secret_id = self._get_param("SecretId")
        secret_string = self._get_param("SecretString")
        secret_binary = self._get_param("SecretBinary")
        return secretsmanager_backends[self.region].update_secret(
            secret_id=secret_id,
            secret_string=secret_string,
            secret_binary=secret_binary,
        )

    def get_random_password(self):
        password_length = self._get_param("PasswordLength", if_none=32)
        exclude_characters = self._get_param("ExcludeCharacters", if_none="")
        exclude_numbers = self._get_param("ExcludeNumbers", if_none=False)
        exclude_punctuation = self._get_param("ExcludePunctuation", if_none=False)
        exclude_uppercase = self._get_param("ExcludeUppercase", if_none=False)
        exclude_lowercase = self._get_param("ExcludeLowercase", if_none=False)
        include_space = self._get_param("IncludeSpace", if_none=False)
        require_each_included_type = self._get_param(
            "RequireEachIncludedType", if_none=True
        )
        return secretsmanager_backends[self.region].get_random_password(
            password_length=password_length,
            exclude_characters=exclude_characters,
            exclude_numbers=exclude_numbers,
            exclude_punctuation=exclude_punctuation,
            exclude_uppercase=exclude_uppercase,
            exclude_lowercase=exclude_lowercase,
            include_space=include_space,
            require_each_included_type=require_each_included_type,
        )

    def describe_secret(self):
        secret_id = self._get_param("SecretId")
        return secretsmanager_backends[self.region].describe_secret(secret_id=secret_id)

    def rotate_secret(self):
        client_request_token = self._get_param("ClientRequestToken")
        rotation_lambda_arn = self._get_param("RotationLambdaARN")
        rotation_rules = self._get_param("RotationRules")
        secret_id = self._get_param("SecretId")
        return secretsmanager_backends[self.region].rotate_secret(
            secret_id=secret_id,
            client_request_token=client_request_token,
            rotation_lambda_arn=rotation_lambda_arn,
            rotation_rules=rotation_rules,
        )

    def put_secret_value(self):
        secret_id = self._get_param("SecretId", if_none="")
        secret_string = self._get_param("SecretString")
        secret_binary = self._get_param("SecretBinary")
        if not secret_binary and not secret_string:
            raise InvalidRequestException(
                "You must provide either SecretString or SecretBinary."
            )
        version_stages = self._get_param("VersionStages", if_none=["AWSCURRENT"])
        return secretsmanager_backends[self.region].put_secret_value(
            secret_id=secret_id,
            secret_binary=secret_binary,
            secret_string=secret_string,
            version_stages=version_stages,
        )

    def list_secret_version_ids(self):
        secret_id = self._get_param("SecretId", if_none="")
        return secretsmanager_backends[self.region].list_secret_version_ids(
            secret_id=secret_id
        )

    def list_secrets(self):
        max_results = self._get_int_param("MaxResults")
        next_token = self._get_param("NextToken")
        secret_list, next_token = secretsmanager_backends[self.region].list_secrets(
            max_results=max_results, next_token=next_token
        )
        return json.dumps(dict(SecretList=secret_list, NextToken=next_token))

    def delete_secret(self):
        secret_id = self._get_param("SecretId")
        recovery_window_in_days = self._get_param("RecoveryWindowInDays")
        force_delete_without_recovery = self._get_param("ForceDeleteWithoutRecovery")
        arn, name, deletion_date = secretsmanager_backends[self.region].delete_secret(
            secret_id=secret_id,
            recovery_window_in_days=recovery_window_in_days,
            force_delete_without_recovery=force_delete_without_recovery,
        )
        return json.dumps(dict(ARN=arn, Name=name, DeletionDate=deletion_date))

    def restore_secret(self):
        secret_id = self._get_param("SecretId")
        arn, name = secretsmanager_backends[self.region].restore_secret(
            secret_id=secret_id
        )
        return json.dumps(dict(ARN=arn, Name=name))

    def get_resource_policy(self):
        secret_id = self._get_param("SecretId")
        return secretsmanager_backends[self.region].get_resource_policy(
            secret_id=secret_id
        )
