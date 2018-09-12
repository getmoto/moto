from __future__ import unicode_literals

from moto.core.responses import BaseResponse

from .models import secretsmanager_backends


class SecretsManagerResponse(BaseResponse):

    def get_secret_value(self):
        secret_id = self._get_param('SecretId')
        version_id = self._get_param('VersionId')
        version_stage = self._get_param('VersionStage')
        return secretsmanager_backends[self.region].get_secret_value(
            secret_id=secret_id,
            version_id=version_id,
            version_stage=version_stage)

    def create_secret(self):
        name = self._get_param('Name')
        secret_string = self._get_param('SecretString')
        return secretsmanager_backends[self.region].create_secret(
            name=name,
            secret_string=secret_string
        )

    def get_random_password(self):
        password_length = self._get_param('PasswordLength', if_none=32)
        exclude_characters = self._get_param('ExcludeCharacters', if_none='')
        exclude_numbers = self._get_param('ExcludeNumbers', if_none=False)
        exclude_punctuation = self._get_param('ExcludePunctuation', if_none=False)
        exclude_uppercase = self._get_param('ExcludeUppercase', if_none=False)
        exclude_lowercase = self._get_param('ExcludeLowercase', if_none=False)
        include_space = self._get_param('IncludeSpace', if_none=False)
        require_each_included_type = self._get_param(
            'RequireEachIncludedType', if_none=True)
        return secretsmanager_backends[self.region].get_random_password(
            password_length=password_length,
            exclude_characters=exclude_characters,
            exclude_numbers=exclude_numbers,
            exclude_punctuation=exclude_punctuation,
            exclude_uppercase=exclude_uppercase,
            exclude_lowercase=exclude_lowercase,
            include_space=include_space,
            require_each_included_type=require_each_included_type
        )

    def describe_secret(self):
        secret_id = self._get_param('SecretId')
        return secretsmanager_backends[self.region].describe_secret(
            secret_id=secret_id
        )
