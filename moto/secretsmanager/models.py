from __future__ import unicode_literals

import time
import json
import uuid

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


class SecretsManagerBackend(BaseBackend):

    def __init__(self, region_name=None, **kwargs):
        super(SecretsManagerBackend, self).__init__()
        self.region = region_name
        self.secrets = {}

    def reset(self):
        region_name = self.region
        self.__dict__ = {}
        self.__init__(region_name)

    def _is_valid_identifier(self, identifier):
        return identifier in self.secrets

    def get_secret_value(self, secret_id, version_id, version_stage):

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException()

        secret = self.secrets[secret_id]

        response = json.dumps({
            "ARN": secret_arn(self.region, secret['secret_id']),
            "Name": secret['name'],
            "VersionId": secret['version_id'],
            "SecretString": secret['secret_string'],
            "VersionStages": [
                "AWSCURRENT",
            ],
            "CreatedDate": secret['createdate']
        })

        return response

    def create_secret(self, name, secret_string, tags, **kwargs):

        generated_version_id = str(uuid.uuid4())

        secret = {
            'secret_string': secret_string,
            'secret_id': name,
            'name': name,
            'createdate': int(time.time()),
            'rotation_enabled': False,
            'rotation_lambda_arn': '',
            'auto_rotate_after_days': 0,
            'version_id': generated_version_id,
            'tags': tags
        }

        self.secrets[name] = secret

        response = json.dumps({
            "ARN": secret_arn(self.region, name),
            "Name": name,
            "VersionId": generated_version_id,
        })

        return response

    def describe_secret(self, secret_id):
        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        secret = self.secrets[secret_id]

        response = json.dumps({
            "ARN": secret_arn(self.region, secret['secret_id']),
            "Name": secret['name'],
            "Description": "",
            "KmsKeyId": "",
            "RotationEnabled": secret['rotation_enabled'],
            "RotationLambdaARN": secret['rotation_lambda_arn'],
            "RotationRules": {
                "AutomaticallyAfterDays": secret['auto_rotate_after_days']
            },
            "LastRotatedDate": None,
            "LastChangedDate": None,
            "LastAccessedDate": None,
            "DeletedDate": None,
            "Tags": secret['tags']
        })

        return response

    def rotate_secret(self, secret_id, client_request_token=None,
                      rotation_lambda_arn=None, rotation_rules=None):

        rotation_days = 'AutomaticallyAfterDays'

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        if client_request_token:
            token_length = len(client_request_token)
            if token_length < 32 or token_length > 64:
                msg = (
                    'ClientRequestToken '
                    'must be 32-64 characters long.'
                )
                raise InvalidParameterException(msg)

        if rotation_lambda_arn:
            if len(rotation_lambda_arn) > 2048:
                msg = (
                    'RotationLambdaARN '
                    'must <= 2048 characters long.'
                )
                raise InvalidParameterException(msg)

        if rotation_rules:
            if rotation_days in rotation_rules:
                rotation_period = rotation_rules[rotation_days]
                if rotation_period < 1 or rotation_period > 1000:
                    msg = (
                        'RotationRules.AutomaticallyAfterDays '
                        'must be within 1-1000.'
                    )
                    raise InvalidParameterException(msg)

        secret = self.secrets[secret_id]

        secret['version_id'] = client_request_token or ''
        secret['rotation_lambda_arn'] = rotation_lambda_arn or ''
        if rotation_rules:
            secret['auto_rotate_after_days'] = rotation_rules.get(rotation_days, 0)
        if secret['auto_rotate_after_days'] > 0:
            secret['rotation_enabled'] = True

        response = json.dumps({
            "ARN": secret_arn(self.region, secret['secret_id']),
            "Name": secret['name'],
            "VersionId": secret['version_id']
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
