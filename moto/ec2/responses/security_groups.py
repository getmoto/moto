from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class SecurityGroups(object):
    def authorize_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.authorize_security_group_egress is not yet implemented')

    def authorize_security_group_ingress(self):
        raise NotImplementedError('SecurityGroups.authorize_security_group_ingress is not yet implemented')

    def create_security_group(self):
        raise NotImplementedError('SecurityGroups.create_security_group is not yet implemented')

    def delete_security_group(self):
        raise NotImplementedError('SecurityGroups.delete_security_group is not yet implemented')

    def describe_security_groups(self):
        raise NotImplementedError('SecurityGroups.describe_security_groups is not yet implemented')

    def revoke_security_group_egress(self):
        raise NotImplementedError('SecurityGroups.revoke_security_group_egress is not yet implemented')

    def revoke_security_group_ingress(self):
        raise NotImplementedError('SecurityGroups.revoke_security_group_ingress is not yet implemented')

