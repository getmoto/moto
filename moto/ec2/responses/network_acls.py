from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class NetworkACLs(object):
    def create_network_acl(self):
        return NotImplemented

    def create_network_acl_entry(self):
        return NotImplemented

    def delete_network_acl(self):
        return NotImplemented

    def delete_network_acl_entry(self):
        return NotImplemented

    def describe_network_acls(self):
        return NotImplemented

    def replace_network_acl_association(self):
        return NotImplemented

    def replace_network_acl_entry(self):
        return NotImplemented

