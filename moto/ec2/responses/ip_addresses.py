from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class IPAddresses(object):
    def assign_private_ip_addresses(self):
        return NotImplemented

    def unassign_private_ip_addresses(self):
        return NotImplemented

