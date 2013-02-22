from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class DHCPOptions(object):
    def associate_dhcp_options(self):
        return NotImplemented

    def create_dhcp_options(self):
        return NotImplemented

    def delete_dhcp_options(self):
        return NotImplemented

    def describe_dhcp_options(self):
        return NotImplemented

