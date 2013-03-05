from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VPNConnections(object):
    def create_vpn_connection(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).create_vpn_connection is not yet implemented')

    def delete_vpn_connection(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).delete_vpn_connection is not yet implemented')

    def describe_vpn_connections(self):
        raise NotImplementedError('VPNConnections(AmazonVPC).describe_vpn_connections is not yet implemented')
