from __future__ import unicode_literals

import time
import json
import uuid
import datetime

import boto3

from moto.core import BaseBackend, BaseModel
from .exceptions import (
    ResourceNotFoundException,
    InvalidParameterException,
    ResourceExistsException,
    InvalidRequestException,
    ClientError
)
from .utils import random_password, secret_arn


AWSCURRENT = 'AWSCURRENT'
AWSPREVIOUS = 'AWSPREVIOUS'
AWSPENDING = 'AWSPENDING'


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

    def _unix_time_secs(self, dt):
        epoch = datetime.datetime.utcfromtimestamp(0)
        return (dt - epoch).total_seconds()

    def get_secret_value(self, secret_id, version_id, version_stage):

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException()

        if not version_id and version_stage:
            # set version_id to match version_stage
            versions_dict = self.secrets[secret_id]['versions']
            for ver_id, ver_val in versions_dict.items():
                if version_stage in ver_val['version_stages']:
                    version_id = ver_id
                    break
            if not version_id:
                raise ResourceNotFoundException()

        # TODO check this part
        if 'deleted_date' in self.secrets[secret_id]:
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the GetSecretValue operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

        secret = self.secrets[secret_id]
        version_id = version_id or secret['default_version_id']

        secret_version = secret['versions'][version_id]

        response_data = {
            "ARN": secret_arn(self.region, secret['secret_id']),
            "Name": secret['name'],
            "VersionId": secret_version['version_id'],
            "VersionStages": list(secret_version['version_stages']),
            "CreatedDate": secret_version['createdate'],
        }

        if 'secret_string' in secret_version:
            response_data["SecretString"] = secret_version['secret_string']

        if 'secret_binary' in secret_version:
            response_data["SecretBinary"] = secret_version['secret_binary']

        response = json.dumps(response_data)

        return response

    def create_secret(self, name, secret_string=None, secret_binary=None, tags={}, **kwargs):

        # error if secret exists
        if name in self.secrets.keys():
            raise ResourceExistsException('A resource with the ID you requested already exists.')

        version_id = self._add_secret(name, secret_string=secret_string, secret_binary=secret_binary, tags=tags)

        response = json.dumps({
            "ARN": secret_arn(self.region, name),
            "Name": name,
            "VersionId": version_id,
        })

        return response

    def _add_secret(self, secret_id, secret_string=None, secret_binary=None, tags={}, version_id=None, version_stages=None):

        if version_stages is None:
            version_stages = [AWSCURRENT]

        if not version_id:
            version_id = str(uuid.uuid4())

        awscurrent_version = self._get_version_with_stage(secret_id, AWSCURRENT)
        awsprevious_version = self._get_version_with_stage(secret_id, AWSPREVIOUS)

        secret_version = {
            'createdate': int(time.time()),
            'version_id': version_id,
            'version_stages': set(version_stages),
        }

        if secret_string is not None:
            secret_version['secret_string'] = secret_string

        if secret_binary is not None:
            secret_version['secret_binary'] = secret_binary

        if secret_id in self.secrets:
            self.secrets[secret_id]['versions'][version_id] = secret_version
        else:
            self.secrets[secret_id] = {
                'versions': {
                    version_id: secret_version
                },
                'default_version_id': version_id,
                'rotation_enabled': False,
                'rotation_lambda_arn': '',
                'auto_rotate_after_days': 0,
                'tags': {},
            }

        # if another stage was not specified, shift AWSCURRENT and AWSPREVIOUS
        if not version_stages or AWSCURRENT in version_stages:
            if awsprevious_version:
                awsprevious_version['version_stages'].remove(AWSPREVIOUS)
            if awscurrent_version:
                awscurrent_version['version_stages'].remove(AWSCURRENT)
                awscurrent_version['version_stages'].update((AWSPREVIOUS,))
            secret_version['version_stages'].update((AWSCURRENT,))
            self.secrets[secret_id]['default_version_id'] = version_id

        secret = self.secrets[secret_id]
        secret['secret_id'] = secret_id
        secret['name'] = secret_id
        secret['tags'] = tags

        return version_id

    def put_secret_value(self, secret_id, secret_string=None, secret_binary=None, version_stages=[AWSCURRENT]):

        version_id = str(uuid.uuid4())

        awscurrent_version = self._get_version_with_stage(secret_id, AWSCURRENT)
        awsprevious_version = self._get_version_with_stage(secret_id, AWSPREVIOUS)

        secret_version = {
            'createdate': int(time.time()),
            'version_id': version_id,
            'version_stages': set(version_stages),
        }

        if secret_string is not None:
            secret_version['secret_string'] = secret_string

        if secret_binary is not None:
            secret_version['secret_binary'] = secret_binary

        if secret_id in self.secrets:
            self.secrets[secret_id]['versions'][version_id] = secret_version
        else:
            self.secrets[secret_id] = {
                'versions': {
                    version_id: secret_version
                },
                'default_version_id': version_id,
                'secret_id': secret_id,
                'name': secret_id,
                'rotation_enabled': False,
                'rotation_lambda_arn': '',
                'auto_rotate_after_days': 0,
                'tags': {},
            }

        # if another stage was not specified, shift AWSCURRENT and AWSPREVIOUS
        if not version_stages or AWSCURRENT in version_stages:
            if awsprevious_version:
                awsprevious_version['version_stages'].remove(AWSPREVIOUS)
            if awscurrent_version:
                awscurrent_version['version_stages'].remove(AWSCURRENT)
                awscurrent_version['version_stages'].update((AWSPREVIOUS,))
            secret_version['version_stages'].update((AWSCURRENT,))
            self.secrets[secret_id]['default_version_id'] = version_id

        response = json.dumps({
            'ARN': secret_arn(self.region, secret_id),
            'Name': secret_id,
            'VersionId': version_id,
            'VersionStages': list(version_stages)
        })

        return response

    def _get_version_with_stage(self, secret_id, stage):
        if secret_id in self.secrets:
            for version_id, version in self.secrets[secret_id]['versions'].items():
                if stage in version['version_stages']:
                    return version
        return None


    def describe_secret(self, secret_id):
        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        secret = self.secrets[secret_id]

        version_ids_to_stages = {}
        for version_id, version in secret['versions'].items():
            version_ids_to_stages[version_id] = version['version_stages']
            version_ids_to_stages[version_id] = list(version['version_stages'])

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
            "DeletedDate": secret.get('deleted_date', None),
            "Tags": secret['tags']
        })

        return response

    def rotate_secret(self, secret_id, client_request_token=None,
                      rotation_lambda_arn=None, rotation_rules=None):

        rotation_days = 'AutomaticallyAfterDays'

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        if 'deleted_date' in self.secrets[secret_id]:
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the RotateSecret operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

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

        old_secret_version = secret['versions'][secret['default_version_id']]
        new_version_id = client_request_token or str(uuid.uuid4())

        self._add_secret(secret_id, old_secret_version['secret_string'], secret['tags'], version_id=new_version_id, version_stages=[AWSCURRENT])

        secret['rotation_lambda_arn'] = rotation_lambda_arn or ''
        if rotation_rules:
            secret['auto_rotate_after_days'] = rotation_rules.get(rotation_days, 0)
        if secret['auto_rotate_after_days'] > 0:
            secret['rotation_enabled'] = True

        if AWSCURRENT in old_secret_version['version_stages']:
            old_secret_version['version_stages'].remove(AWSCURRENT)

        response = json.dumps({
            "ARN": secret_arn(self.region, secret['secret_id']),
            "Name": secret['name'],
            "VersionId": new_version_id
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

    def list_secret_version_ids(self, secret_id):
        secret = self.secrets[secret_id]

        version_list = []
        for version_id, version in secret['versions'].items():
            version_list.append({
                'CreatedDate': int(time.time()),
                'LastAccessedDate': int(time.time()),
                'VersionId': version_id,
                'VersionStages': list(version['version_stages']),
            })

        response = json.dumps({
            'ARN': secret['secret_id'],
            'Name': secret['name'],
            'NextToken': '',
            'Versions': version_list,
        })

        return response

    def list_secrets(self, max_results, next_token):
        # TODO implement pagination and limits

        secret_list = []
        for secret in self.secrets.values():

            versions_to_stages = {}
            for version_id, version in secret['versions'].items():
                versions_to_stages[version_id] = list(version['version_stages'])

            secret_list.append({
                "ARN": secret_arn(self.region, secret['secret_id']),
                "DeletedDate": secret.get('deleted_date', None),
                "Description": "",
                "KmsKeyId": "",
                "LastAccessedDate": None,
                "LastChangedDate": None,
                "LastRotatedDate": None,
                "Name": secret['name'],
                "RotationEnabled": secret['rotation_enabled'],
                "RotationLambdaARN": secret['rotation_lambda_arn'],
                "RotationRules": {
                    "AutomaticallyAfterDays": secret['auto_rotate_after_days']
                },
                "SecretVersionsToStages": versions_to_stages,
                "Tags": secret['tags']
            })

        return secret_list, None

    def delete_secret(self, secret_id, recovery_window_in_days, force_delete_without_recovery):

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        if 'deleted_date' in self.secrets[secret_id]:
            raise InvalidRequestException(
                "An error occurred (InvalidRequestException) when calling the DeleteSecret operation: You tried to \
                perform the operation on a secret that's currently marked deleted."
            )

        if recovery_window_in_days and force_delete_without_recovery:
            raise InvalidParameterException(
                "An error occurred (InvalidParameterException) when calling the DeleteSecret operation: You can't \
                use ForceDeleteWithoutRecovery in conjunction with RecoveryWindowInDays."
            )

        if recovery_window_in_days and (recovery_window_in_days < 7 or recovery_window_in_days > 30):
            raise InvalidParameterException(
                "An error occurred (InvalidParameterException) when calling the DeleteSecret operation: The \
                RecoveryWindowInDays value must be between 7 and 30 days (inclusive)."
            )

        deletion_date = datetime.datetime.utcnow()

        if force_delete_without_recovery:
            secret = self.secrets.pop(secret_id, None)
        else:
            deletion_date += datetime.timedelta(days=recovery_window_in_days or 30)
            self.secrets[secret_id]['deleted_date'] = self._unix_time_secs(deletion_date)
            secret = self.secrets.get(secret_id, None)

        if not secret:
            raise ResourceNotFoundException

        arn = secret_arn(self.region, secret['secret_id'])
        name = secret['name']

        return arn, name, self._unix_time_secs(deletion_date)

    def restore_secret(self, secret_id):

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        self.secrets[secret_id].pop('deleted_date', None)

        secret = self.secrets[secret_id]

        arn = secret_arn(self.region, secret['secret_id'])
        name = secret['name']

        return arn, name

    def update_secret_version_stage(self, secret_id, version_stage, remove_from_version_id, move_to_version_id):

        if not self._is_valid_identifier(secret_id):
            raise ResourceNotFoundException

        if not remove_from_version_id and not move_to_version_id:
            raise InvalidRequestException(f'To update staging label {version_stage}, you must specify RemoveFromVersionId and/or MoveToVersionId.')

        # do not let AWSCURRENT or AWSPREVIOUS be removed
        if version_stage in [AWSCURRENT, AWSPREVIOUS] and remove_from_version_id and not move_to_version_id:
            raise InvalidParameterException(f'You can only move staging label {version_stage} to a different secret version. It can?t be completely removed.')

        secret = self.secrets[secret_id]

        # get the AWSCURRENT and AWSPREVIOUS versions
        awscurrent_version = self._get_version_with_stage(secret_id, AWSCURRENT)
        awsprevious_version = self._get_version_with_stage(secret_id, AWSPREVIOUS)
        awspending_version = self._get_version_with_stage(secret_id, AWSPENDING)

        # add/remove stages
        if remove_from_version_id:
            secret['versions'][remove_from_version_id]['version_stages'].remove(version_stage)
        if move_to_version_id:
            # remove that stage from current versions
            old_version = self._get_version_with_stage(secret_id, version_stage)
            if old_version:
                old_version['version_stages'].remove(version_stage)
            secret['versions'][move_to_version_id]['version_stages'].update((version_stage,))

        # update AWS* stages
        if version_stage == AWSCURRENT and move_to_version_id:
            if awsprevious_version and AWSPREVIOUS in awsprevious_version['version_stages']:
                awsprevious_version['version_stages'].remove(AWSPREVIOUS)
            if awscurrent_version:
                if AWSCURRENT in awscurrent_version['version_stages']:
                    awscurrent_version['version_stages'].remove(AWSCURRENT)
                awscurrent_version['version_stages'].update((AWSPREVIOUS,))
            secret['versions'][move_to_version_id]['version_stages'].update((AWSCURRENT,))
            if awspending_version:
                awspending_version['version_stages'].remove(AWSPENDING)
            self.secrets[secret_id]['default_version_id'] = move_to_version_id

        arn = secret_arn(self.region, secret['secret_id'])
        name = secret['name']

        return arn, name


available_regions = (
    boto3.session.Session().get_available_regions("secretsmanager")
)
secretsmanager_backends = {region: SecretsManagerBackend(region_name=region)
                           for region in available_regions}
