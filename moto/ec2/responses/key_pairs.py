from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class KeyPairs(object):
    def create_key_pair(self):
        return NotImplemented

    def delete_key_pair(self):
        return NotImplemented

    def describe_key_pairs(self):
        return NotImplemented

    def import_key_pair(self):
        return NotImplemented

