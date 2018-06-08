from __future__ import unicode_literals

from moto.core.responses import BaseResponse

from .models import secretsmanager_backends


class SecretsManagerResponse(BaseResponse):

    def get_secret_value(self):
        secret_id = self.get_param('SecretId')
        version_id = self.get_param('VersionId')
        version_stage = self.get_param('VersionStage')
        return secretsmanager_backends[self.region].get_secret_value(
            secret_id=secret_id,
            version_id=version_id,
            version_stage=version_stage)
