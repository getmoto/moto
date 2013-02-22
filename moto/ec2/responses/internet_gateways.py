from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class InternetGateways(object):
    def attach_internet_gateway(self):
        return NotImplemented

    def create_internet_gateway(self):
        return NotImplemented

    def delete_internet_gateway(self):
        return NotImplemented

    def describe_internet_gateways(self):
        return NotImplemented

    def detach_internet_gateway(self):
        return NotImplemented

