from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ElasticIPAddresses(object):
    def allocate_address(self):
        return NotImplemented

    def associate_address(self):
        return NotImplemented

    def describe_addresses(self):
        return NotImplemented

    def disassociate_address(self):
        return NotImplemented

    def release_address(self):
        return NotImplemented

