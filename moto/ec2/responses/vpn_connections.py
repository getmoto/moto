from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VPNConnections(object):
    def create_vpn_connection(self):
        return NotImplemented

    def delete_vpn_connection(self):
        return NotImplemented

    def describe_vpn_connections(self):
        return NotImplemented

