from __future__ import unicode_literals

import datetime
import json

import boto3

from moto.core import BaseBackend, BaseModel


class SecretsManager(BaseModel):

    def __init__(self, region_name, **kwargs):
        self.secret_id = kwargs.get('secret_id', '')
        self.version_id = kwargs.get('version_id', '')
        self.string_id = kwargs.get('string_id', '')

class SecretsManagerBackend(BaseBackend):

    def __init__(self, region_name=None):
        super(SecretsManagerBackend, self).__init__()
        self.region = region_name

    def get_secret_value(self, secret_id, version_id, string_id):

        response = json.dumps({
            "ARN": self.secret_arn(),
            "Name": self.secret_id,
            "VersionId": "A435958A-D821-4193-B719-B7769357AER4",
            "SecretBinary": b"testbytes",
            "SecretString": "mysecretstring",
            "VersionStages": [
                "AWSCURRENT",
            ],
            "CreatedDate": datetime.datetime.utcnow()
        })

        return response

    def secret_arn(self):
        return "arn:aws:secretsmanager:{0}:1234567890:secret:{1}-rIjad".format(
            self.region, self.secret_id)


available_regions = boto3.session.Session().get_available_regions("secretsmanager")
print(available_regions)
secretsmanager_backends = {region: SecretsManagerBackend(region_name=region) for region in available_regions}
