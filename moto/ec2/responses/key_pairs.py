from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class KeyPairs(object):
    def create_key_pair(self):
        raise NotImplementedError('KeyPairs.create_key_pair is not yet implemented')

    def delete_key_pair(self):
        raise NotImplementedError('KeyPairs.delete_key_pair is not yet implemented')

    def describe_key_pairs(self):
        raise NotImplementedError('KeyPairs.describe_key_pairs is not yet implemented')

    def import_key_pair(self):
        raise NotImplementedError('KeyPairs.import_key_pair is not yet implemented')
