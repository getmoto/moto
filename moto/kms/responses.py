from __future__ import unicode_literals

import base64
import json
import re
import six

from boto.exception import JSONResponseError
from boto.kms.exceptions import AlreadyExistsException, NotFoundException

from moto.core.responses import BaseResponse
from .models import kms_backends

reserved_aliases = [
    'alias/aws/ebs',
    'alias/aws/s3',
    'alias/aws/redshift',
    'alias/aws/rds',
]


class KmsResponse(BaseResponse):

    @property
    def parameters(self):
        return json.loads(self.body)

    @property
    def kms_backend(self):
        return kms_backends[self.region]

    def create_key(self):
        policy = self.parameters.get('Policy')
        key_usage = self.parameters.get('KeyUsage')
        description = self.parameters.get('Description')

        key = self.kms_backend.create_key(
            policy, key_usage, description, self.region)
        return json.dumps(key.to_dict())

    def describe_key(self):
        key_id = self.parameters.get('KeyId')
        try:
            key = self.kms_backend.describe_key(
                self.kms_backend.get_key_id(key_id))
        except KeyError:
            headers = dict(self.headers)
            headers['status'] = 404
            return "{}", headers
        return json.dumps(key.to_dict())

    def list_keys(self):
        keys = self.kms_backend.list_keys()

        return json.dumps({
            "Keys": [
                {
                    "KeyArn": key.arn,
                    "KeyId": key.id,
                } for key in keys
            ],
            "NextMarker": None,
            "Truncated": False,
        })

    def create_alias(self):
        alias_name = self.parameters['AliasName']
        target_key_id = self.parameters['TargetKeyId']
        region = self.region

        if not alias_name.startswith('alias/'):
            raise JSONResponseError(400, 'Bad Request',
                                    body={'message': 'Invalid identifier', '__type': 'ValidationException'})

        if alias_name in reserved_aliases:
            raise JSONResponseError(400, 'Bad Request', body={
                                    '__type': 'NotAuthorizedException'})

        if ':' in alias_name:
            raise JSONResponseError(400, 'Bad Request', body={
                'message': '{alias_name} contains invalid characters for an alias'.format(**locals()),
                '__type': 'ValidationException'})

        if not re.match(r'^[a-zA-Z0-9:/_-]+$', alias_name):
            raise JSONResponseError(400, 'Bad Request', body={
                'message': "1 validation error detected: Value '{alias_name}' at 'aliasName' failed to satisfy constraint: Member must satisfy regular expression pattern: ^[a-zA-Z0-9:/_-]+$"
                                    .format(**locals()),
                                    '__type': 'ValidationException'})

        if self.kms_backend.alias_exists(target_key_id):
            raise JSONResponseError(400, 'Bad Request', body={
                'message': 'Aliases must refer to keys. Not aliases',
                '__type': 'ValidationException'})

        if self.kms_backend.alias_exists(alias_name):
            raise AlreadyExistsException(400, 'Bad Request', body={
                'message': 'An alias with the name arn:aws:kms:{region}:012345678912:{alias_name} already exists'
                                         .format(**locals()), '__type': 'AlreadyExistsException'})

        self.kms_backend.add_alias(target_key_id, alias_name)

        return json.dumps(None)

    def delete_alias(self):
        alias_name = self.parameters['AliasName']
        region = self.region

        if not alias_name.startswith('alias/'):
            raise JSONResponseError(400, 'Bad Request',
                                    body={'message': 'Invalid identifier', '__type': 'ValidationException'})

        if not self.kms_backend.alias_exists(alias_name):
            raise NotFoundException(400, 'Bad Request', body={
                'message': 'Alias arn:aws:kms:{region}:012345678912:{alias_name} is not found.'.format(**locals()),
                '__type': 'NotFoundException'})

        self.kms_backend.delete_alias(alias_name)

        return json.dumps(None)

    def list_aliases(self):
        region = self.region

        response_aliases = [
            {
                'AliasArn': u'arn:aws:kms:{region}:012345678912:{reserved_alias}'.format(region=region,
                                                                                         reserved_alias=reserved_alias),
                'AliasName': reserved_alias
            } for reserved_alias in reserved_aliases
        ]

        backend_aliases = self.kms_backend.get_all_aliases()
        for target_key_id, aliases in backend_aliases.items():
            for alias_name in aliases:
                response_aliases.append({
                    'AliasArn': u'arn:aws:kms:{region}:012345678912:{alias_name}'.format(region=region,
                                                                                         alias_name=alias_name),
                    'AliasName': alias_name,
                    'TargetKeyId': target_key_id,
                })

        return json.dumps({
            'Truncated': False,
            'Aliases': response_aliases,
        })

    def enable_key_rotation(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.enable_key_rotation(key_id)
        except KeyError:
            raise JSONResponseError(404, 'Not Found', body={
                'message': "Key 'arn:aws:kms:{region}:012345678912:key/{key_id}' does not exist".format(region=self.region, key_id=key_id),
                '__type': 'NotFoundException'})

        return json.dumps(None)

    def disable_key_rotation(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.disable_key_rotation(key_id)
        except KeyError:
            raise JSONResponseError(404, 'Not Found', body={
                'message': "Key 'arn:aws:kms:{region}:012345678912:key/{key_id}' does not exist".format(region=self.region, key_id=key_id),
                '__type': 'NotFoundException'})
        return json.dumps(None)

    def get_key_rotation_status(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            rotation_enabled = self.kms_backend.get_key_rotation_status(key_id)
        except KeyError:
            raise JSONResponseError(404, 'Not Found', body={
                'message': "Key 'arn:aws:kms:{region}:012345678912:key/{key_id}' does not exist".format(region=self.region, key_id=key_id),
                '__type': 'NotFoundException'})
        return json.dumps({'KeyRotationEnabled': rotation_enabled})

    def put_key_policy(self):
        key_id = self.parameters.get('KeyId')
        policy_name = self.parameters.get('PolicyName')
        policy = self.parameters.get('Policy')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        _assert_default_policy(policy_name)

        try:
            self.kms_backend.put_key_policy(key_id, policy)
        except KeyError:
            raise JSONResponseError(404, 'Not Found', body={
                'message': "Key 'arn:aws:kms:{region}:012345678912:key/{key_id}' does not exist".format(region=self.region, key_id=key_id),
                '__type': 'NotFoundException'})

        return json.dumps(None)

    def get_key_policy(self):
        key_id = self.parameters.get('KeyId')
        policy_name = self.parameters.get('PolicyName')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        _assert_default_policy(policy_name)

        try:
            return json.dumps({'Policy': self.kms_backend.get_key_policy(key_id)})
        except KeyError:
            raise JSONResponseError(404, 'Not Found', body={
                'message': "Key 'arn:aws:kms:{region}:012345678912:key/{key_id}' does not exist".format(region=self.region, key_id=key_id),
                '__type': 'NotFoundException'})

    def list_key_policies(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.describe_key(key_id)
        except KeyError:
            raise JSONResponseError(404, 'Not Found', body={
                'message': "Key 'arn:aws:kms:{region}:012345678912:key/{key_id}' does not exist".format(region=self.region, key_id=key_id),
                '__type': 'NotFoundException'})

        return json.dumps({'Truncated': False, 'PolicyNames': ['default']})

    def encrypt(self):
        """
        We perform no encryption, we just encode the value as base64 and then
        decode it in decrypt().
        """
        value = self.parameters.get("Plaintext")
        if isinstance(value, six.text_type):
            value = value.encode('utf-8')
        return json.dumps({"CiphertextBlob": base64.b64encode(value).decode("utf-8")})

    def decrypt(self):
        value = self.parameters.get("CiphertextBlob")
        return json.dumps({"Plaintext": base64.b64decode(value).decode("utf-8")})


def _assert_valid_key_id(key_id):
    if not re.match(r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$', key_id, re.IGNORECASE):
        raise JSONResponseError(404, 'Not Found', body={
                                'message': ' Invalid keyId', '__type': 'NotFoundException'})


def _assert_default_policy(policy_name):
    if policy_name != 'default':
        raise JSONResponseError(404, 'Not Found', body={
            'message': "No such policy exists",
            '__type': 'NotFoundException'})
