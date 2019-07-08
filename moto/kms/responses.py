from __future__ import unicode_literals

import base64
import json
import re
import six

from moto.core.responses import BaseResponse
from .models import kms_backends
from .exceptions import NotFoundException, ValidationException, AlreadyExistsException, NotAuthorizedException

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

    def update_key_description(self):
        key_id = self.parameters.get('KeyId')
        description = self.parameters.get('Description')

        self.kms_backend.update_key_description(key_id, description)
        return json.dumps(None)

    def tag_resource(self):
        key_id = self.parameters.get('KeyId')
        tags = self.parameters.get('Tags')
        self.kms_backend.tag_resource(key_id, tags)
        return json.dumps({})

    def list_resource_tags(self):
        key_id = self.parameters.get('KeyId')
        tags = self.kms_backend.list_resource_tags(key_id)
        return json.dumps({
            "Tags": tags,
            "NextMarker": None,
            "Truncated": False,
        })

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

        if not alias_name.startswith('alias/'):
            raise ValidationException('Invalid identifier')

        if alias_name in reserved_aliases:
            raise NotAuthorizedException()

        if ':' in alias_name:
            raise ValidationException('{alias_name} contains invalid characters for an alias'.format(alias_name=alias_name))

        if not re.match(r'^[a-zA-Z0-9:/_-]+$', alias_name):
            raise ValidationException("1 validation error detected: Value '{alias_name}' at 'aliasName' "
                                  "failed to satisfy constraint: Member must satisfy regular "
                                  "expression pattern: ^[a-zA-Z0-9:/_-]+$"
                                      .format(alias_name=alias_name))

        if self.kms_backend.alias_exists(target_key_id):
            raise ValidationException('Aliases must refer to keys. Not aliases')

        if self.kms_backend.alias_exists(alias_name):
            raise AlreadyExistsException('An alias with the name arn:aws:kms:{region}:012345678912:{alias_name} '
                                         'already exists'.format(region=self.region, alias_name=alias_name))

        self.kms_backend.add_alias(target_key_id, alias_name)

        return json.dumps(None)

    def delete_alias(self):
        alias_name = self.parameters['AliasName']

        if not alias_name.startswith('alias/'):
            raise ValidationException('Invalid identifier')

        if not self.kms_backend.alias_exists(alias_name):
            raise NotFoundException('Alias arn:aws:kms:{region}:012345678912:'
                                    '{alias_name} is not found.'.format(region=self.region, alias_name=alias_name))

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
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))

        return json.dumps(None)

    def disable_key_rotation(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.disable_key_rotation(key_id)
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))
        return json.dumps(None)

    def get_key_rotation_status(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            rotation_enabled = self.kms_backend.get_key_rotation_status(key_id)
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))
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
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))

        return json.dumps(None)

    def get_key_policy(self):
        key_id = self.parameters.get('KeyId')
        policy_name = self.parameters.get('PolicyName')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        _assert_default_policy(policy_name)

        try:
            return json.dumps({'Policy': self.kms_backend.get_key_policy(key_id)})
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))

    def list_key_policies(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.describe_key(key_id)
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))

        return json.dumps({'Truncated': False, 'PolicyNames': ['default']})

    def encrypt(self):
        """
        We perform no encryption, we just encode the value as base64 and then
        decode it in decrypt().
        """
        value = self.parameters.get("Plaintext")
        if isinstance(value, six.text_type):
            value = value.encode('utf-8')
        return json.dumps({"CiphertextBlob": base64.b64encode(value).decode("utf-8"), 'KeyId': 'key_id'})

    def decrypt(self):
        # TODO refuse decode if EncryptionContext is not the same as when it was encrypted / generated

        value = self.parameters.get("CiphertextBlob")
        try:
            return json.dumps({"Plaintext": base64.b64decode(value).decode("utf-8")})
        except UnicodeDecodeError:
            # Generate data key will produce random bytes which when decrypted is still returned as base64
            return json.dumps({"Plaintext": value})

    def disable_key(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.disable_key(key_id)
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))
        return json.dumps(None)

    def enable_key(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.enable_key(key_id)
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))
        return json.dumps(None)

    def cancel_key_deletion(self):
        key_id = self.parameters.get('KeyId')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            self.kms_backend.cancel_key_deletion(key_id)
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))
        return json.dumps({'KeyId': key_id})

    def schedule_key_deletion(self):
        key_id = self.parameters.get('KeyId')
        if self.parameters.get('PendingWindowInDays') is None:
            pending_window_in_days = 30
        else:
            pending_window_in_days = self.parameters.get('PendingWindowInDays')
        _assert_valid_key_id(self.kms_backend.get_key_id(key_id))
        try:
            return json.dumps({
                'KeyId': key_id,
                'DeletionDate': self.kms_backend.schedule_key_deletion(key_id, pending_window_in_days)
            })
        except KeyError:
            raise NotFoundException("Key 'arn:aws:kms:{region}:012345678912:key/"
                                    "{key_id}' does not exist".format(region=self.region, key_id=key_id))

    def generate_data_key(self):
        key_id = self.parameters.get('KeyId')
        encryption_context = self.parameters.get('EncryptionContext')
        number_of_bytes = self.parameters.get('NumberOfBytes')
        key_spec = self.parameters.get('KeySpec')
        grant_tokens = self.parameters.get('GrantTokens')

        # Param validation
        if key_id.startswith('alias'):
            if self.kms_backend.get_key_id_from_alias(key_id) is None:
                raise NotFoundException('Alias arn:aws:kms:{region}:012345678912:{alias_name} is not found.'.format(
                                        region=self.region, alias_name=key_id))
        else:
            if self.kms_backend.get_key_id(key_id) not in self.kms_backend.keys:
                raise NotFoundException('Invalid keyId')

        if number_of_bytes and (number_of_bytes > 1024 or number_of_bytes < 0):
            raise ValidationException("1 validation error detected: Value '2048' at 'numberOfBytes' failed "
                                  "to satisfy constraint: Member must have value less than or "
                                  "equal to 1024")

        if key_spec and key_spec not in ('AES_256', 'AES_128'):
            raise ValidationException("1 validation error detected: Value 'AES_257' at 'keySpec' failed "
                                  "to satisfy constraint: Member must satisfy enum value set: "
                                  "[AES_256, AES_128]")
        if not key_spec and not number_of_bytes:
            raise ValidationException("Please specify either number of bytes or key spec.")
        if key_spec and number_of_bytes:
            raise ValidationException("Please specify either number of bytes or key spec.")

        plaintext, key_arn = self.kms_backend.generate_data_key(key_id, encryption_context,
                                                                number_of_bytes, key_spec, grant_tokens)

        plaintext = base64.b64encode(plaintext).decode()

        return json.dumps({
            'CiphertextBlob': plaintext,
            'Plaintext': plaintext,
            'KeyId': key_arn  # not alias
        })

    def generate_data_key_without_plaintext(self):
        result = json.loads(self.generate_data_key())
        del result['Plaintext']

        return json.dumps(result)


def _assert_valid_key_id(key_id):
    if not re.match(r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$', key_id, re.IGNORECASE):
        raise NotFoundException('Invalid keyId')


def _assert_default_policy(policy_name):
    if policy_name != 'default':
        raise NotFoundException("No such policy exists")
