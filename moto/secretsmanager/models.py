from __future__ import unicode_literals

import time
import json

import boto3

from moto.core import BaseBackend, BaseModel


class SecretsManager(BaseModel):

    def __init__(self, region_name, **kwargs):
        self.secret_id = kwargs.get('secret_id', '')
        self.version_id = kwargs.get('version_id', '')
        self.version_stage = kwargs.get('version_stage', '')

class SecretsManagerBackend(BaseBackend):

    def __init__(self, region_name=None, **kwargs):
        super(SecretsManagerBackend, self).__init__()
        self.region = region_name
        self.secret_id = kwargs.get('secret_id', '')
        self.createdate = int(time.time())

    def get_secret_value(self, secret_id, version_id, version_stage):

        response = json.dumps({
            "ARN": self.secret_arn(),
            "Name": self.secret_id,
            "VersionId": "A435958A-D821-4193-B719-B7769357AER4",
            "SecretString": "mysecretstring",
            "VersionStages": [
                "AWSCURRENT",
            ],
            "CreatedDate": "2018-05-23 13:16:57.198000"
        })

        return response

    def secret_arn(self):
        return "arn:aws:secretsmanager:{0}:1234567890:secret:{1}-rIjad".format(
            self.region, self.secret_id)


available_regions = boto3.session.Session().get_available_regions("secretsmanager")
print(available_regions)
secretsmanager_backends = {region: SecretsManagerBackend(region_name=region) for region in available_regions}
