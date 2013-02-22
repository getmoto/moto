from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class Subnets(object):
    def create_subnet(self):
        return NotImplemented

    def delete_subnet(self):
        return NotImplemented

    def describe_subnets(self):
        return NotImplemented

