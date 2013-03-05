from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class DHCPOptions(object):
    def associate_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).associate_dhcp_options is not yet implemented')

    def create_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).create_dhcp_options is not yet implemented')

    def delete_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).delete_dhcp_options is not yet implemented')

    def describe_dhcp_options(self):
        raise NotImplementedError('DHCPOptions(AmazonVPC).describe_dhcp_options is not yet implemented')
