from __future__ import unicode_literals

import time
import json

import boto3

from moto.core import BaseBackend, BaseModel
from .exceptions import ResourceNotFoundException


class SecretsManager(BaseModel):

    def __init__(self, region_name, **kwargs):
        self.region = region_name
        self.secret_id = kwargs.get('secret_id', '')
        self.version_id = kwargs.get('version_id', '')
        self.version_stage = kwargs.get('version_stage', '')
        self.secret_string = ''


class SecretsManagerBackend(BaseBackend):

    def __init__(self, region_name=None, **kwargs):
        super(SecretsManagerBackend, self).__init__()
        self.region = region_name
        self.secret_id = kwargs.get('secret_id', '')
        self.name = kwargs.get('name', '')
        self.createdate = int(time.time())
        self.secret_string = ''

    def reset(self):
        region_name = self.region
        self.__dict__ = {}
        self.__init__(region_name)

    def get_secret_value(self, secret_id, version_id, version_stage):

        if self.secret_id == '':
            raise ResourceNotFoundException()

        response = json.dumps({
            "ARN": self.secret_arn(self.region, self.secret_id),
            "Name": self.secret_id,
            "VersionId": "A435958A-D821-4193-B719-B7769357AER4",
            "SecretString": self.secret_string,
            "VersionStages": [
                "AWSCURRENT",
            ],
            "CreatedDate": "2018-05-23 13:16:57.198000"
        })

        return response

    def create_secret(self, name, secret_string, **kwargs):

        self.secret_string = secret_string
        self.secret_id = name

        response = json.dumps({
            "ARN": self.secret_arn(self.region, name),
            "Name": self.secret_id,
            "VersionId": "A435958A-D821-4193-B719-B7769357AER4",
        })

        return response

    def secret_arn(self, region, secret_id):
        return "arn:aws:secretsmanager:{0}:1234567890:secret:{1}-rIjad".format(
            region, secret_id)


available_regions = (
    boto3.session.Session().get_available_regions("secretsmanager")
)
secretsmanager_backends = {region: SecretsManagerBackend(region_name=region)
                           for region in available_regions}
