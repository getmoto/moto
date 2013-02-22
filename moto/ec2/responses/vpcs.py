from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VPCs(object):
    def create_vpc(self):
        return NotImplemented

    def delete_vpc(self):
        return NotImplemented

    def describe_vpcs(self):
        return NotImplemented

