from __future__ import unicode_literals

from collections import defaultdict

from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends


class Parameter(BaseModel):
    def __init__(self, name, value, type, description, keyid):
        self.name = name
        self.type = type
        self.description = description
        self.keyid = keyid

        if self.type == 'SecureString':
            self.value = self.encrypt(value)
        else:
            self.value = value

    def encrypt(self, value):
        return 'kms:{}:'.format(self.keyid or 'default') + value

    def decrypt(self, value):
        if self.type != 'SecureString':
            return value

        prefix = 'kms:{}:'.format(self.keyid or 'default')
        if value.startswith(prefix):
            return value[len(prefix):]

    def response_object(self, decrypt=False):
        r = {
            'Name': self.name,
            'Type': self.type,
            'Value': self.decrypt(self.value) if decrypt else self.value
        }
        if self.keyid:
            r['KeyId'] = self.keyid
        return r


class SimpleSystemManagerBackend(BaseBackend):

    def __init__(self):
        self._parameters = {}
        self._resource_tags = defaultdict(lambda: defaultdict(dict))

    def delete_parameter(self, name):
        try:
            del self._parameters[name]
        except KeyError:
            pass

    def delete_parameters(self, names):
        result = []
        for name in names:
            try:
                del self._parameters[name]
                result.append(name)
            except KeyError:
                pass
        return result

    def get_all_parameters(self):
        result = []
        for k, _ in self._parameters.items():
            result.append(self._parameters[k])
        return result

    def get_parameters(self, names, with_decryption):
        result = []
        for name in names:
            if name in self._parameters:
                result.append(self._parameters[name])
        return result

    def put_parameter(self, name, description, value, type, keyid, overwrite):
        if not overwrite and name in self._parameters:
            return
        self._parameters[name] = Parameter(
            name, value, type, description, keyid)

    def add_tags_to_resource(self, resource_type, resource_id, tags):
        for key, value in tags.items():
            self._resource_tags[resource_type][resource_id][key] = value

    def remove_tags_from_resource(self, resource_type, resource_id, keys):
        tags = self._resource_tags[resource_type][resource_id]
        for key in keys:
            if key in tags:
                del tags[key]

    def list_tags_for_resource(self, resource_type, resource_id):
        return self._resource_tags[resource_type][resource_id]


ssm_backends = {}
for region, ec2_backend in ec2_backends.items():
    ssm_backends[region] = SimpleSystemManagerBackend()
