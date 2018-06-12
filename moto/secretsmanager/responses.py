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
