from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class SecurityGroups(object):
    def authorize_security_group_egress(self):
        return NotImplemented

    def authorize_security_group_ingress(self):
        return NotImplemented

    def create_security_group(self):
        return NotImplemented

    def delete_security_group(self):
        return NotImplemented

    def describe_security_groups(self):
        return NotImplemented

    def revoke_security_group_egress(self):
        return NotImplemented

    def revoke_security_group_ingress(self):
        return NotImplemented

