from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VirtualPrivateGateways(object):
    def attach_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).attach_vpn_gateway is not yet implemented')

    def create_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).create_vpn_gateway is not yet implemented')

    def delete_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).delete_vpn_gateway is not yet implemented')

    def describe_vpn_gateways(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).describe_vpn_gateways is not yet implemented')

    def detach_vpn_gateway(self):
        raise NotImplementedError('VirtualPrivateGateways(AmazonVPC).detach_vpn_gateway is not yet implemented')
