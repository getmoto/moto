from __future__ import unicode_literals

import time
import json

import boto3

from moto.core import BaseBackend, BaseModel
from .exceptions import (
    ResourceNotFoundException,
    InvalidParameterException,
    ClientError
)
from .utils import random_password, secret_arn


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
        self.rotation_enabled = False
        self.rotation_lambda_arn = ''
        self.auto_rotate_after_days = 0

    def reset(self):
        region_name = self.region
        self.__dict__ = {}
        self.__init__(region_name)

    def _is_valid_identifier(self, identifier):
        return identifier in (self.name, self.secret_id)

    def get_secret_value(self, secret_id, version_id, version_stage):

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException()

        response = json.dumps({
            "ARN": secret_arn(self.region, self.secret_id),
            "Name": self.name,
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
        self.name = name

        response = json.dumps({
            "ARN": secret_arn(self.region, name),
            "Name": self.name,
            "VersionId": "A435958A-D821-4193-B719-B7769357AER4",
        })

        return response

    def describe_secret(self, secret_id):
        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        response = json.dumps({
            "ARN": secret_arn(self.region, self.secret_id),
            "Name": self.name,
            "Description": "",
            "KmsKeyId": "",
            "RotationEnabled": self.rotation_enabled,
            "RotationLambdaARN": self.rotation_lambda_arn,
            "RotationRules": {
                "AutomaticallyAfterDays": self.auto_rotate_after_days
            },
            "LastRotatedDate": None,
            "LastChangedDate": None,
            "LastAccessedDate": None,
            "DeletedDate": None,
            "Tags": [
                {
                    "Key": "",
                    "Value": ""
                },
            ]
        })

        return response

    def get_random_password(self, password_length,
                            exclude_characters, exclude_numbers,
                            exclude_punctuation, exclude_uppercase,
                            exclude_lowercase, include_space,
                            require_each_included_type):
        # password size must have value less than or equal to 4096
        if password_length > 4096:
            raise ClientError(
                "ClientError: An error occurred (ValidationException) \
                when calling the GetRandomPassword operation: 1 validation error detected: Value '{}' at 'passwordLength' \
                failed to satisfy constraint: Member must have value less than or equal to 4096".format(password_length))
        if password_length < 4:
            raise InvalidParameterException(
                "InvalidParameterException: An error occurred (InvalidParameterException) \
                when calling the GetRandomPassword operation: Password length is too short based on the required types.")

        response = json.dumps({
            "RandomPassword": random_password(password_length,
                                              exclude_characters,
                                              exclude_numbers,
                                              exclude_punctuation,
                                              exclude_uppercase,
                                              exclude_lowercase,
                                              include_space,
                                              require_each_included_type)
        })

        return response


available_regions = (
    boto3.session.Session().get_available_regions("secretsmanager")
)
secretsmanager_backends = {region: SecretsManagerBackend(region_name=region)
                           for region in available_regions}
