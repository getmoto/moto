from __future__ import unicode_literals

import datetime
import json

import boto.secretsmanager

from moto.core import BaseBackend, BaseModel

class SecretsManager(BaseModel):

    def __init__(self, region, **kwargs):
        self.secret_id = kwargs.get('secret_id', '')
        self.version_id = kwargs.get('version_id', '')
        self.string_id = kwargs.get('string_id', '')

class SecretsManagerBackend(BaseBackend):

    def __init__(self, region):
        super(SecretsManagerBackend, self).__init__()
        self.region = region

    def get_secret_value(self, secret_id, version_id, string_id):

        secret_response = SecretsManager(self.region, secret_id=secret_id,
            version_id=version_id,
            string_id=string_id)

        response = json.dumps({
            "ARN": secret_arn,
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

secretsmanager_backends = {}
for regin in boto.secretsmanager.regions():
    secretsmanager_backends[region.name] = SecretsManagerBackend(region.name)
