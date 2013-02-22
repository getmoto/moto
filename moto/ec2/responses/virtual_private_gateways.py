from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VirtualPrivateGateways(object):
    def attach_vpn_gateway(self):
        return NotImplemented

    def create_vpn_gateway(self):
        return NotImplemented

    def delete_vpn_gateway(self):
        return NotImplemented

    def describe_vpn_gateways(self):
        return NotImplemented

    def detach_vpn_gateway(self):
        return NotImplemented

