from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VPCs(object):
    def create_vpc(self):
        raise NotImplementedError('VPCs(AmazonVPC).create_vpc is not yet implemented')

    def delete_vpc(self):
        raise NotImplementedError('VPCs(AmazonVPC).delete_vpc is not yet implemented')

    def describe_vpcs(self):
        raise NotImplementedError('VPCs(AmazonVPC).describe_vpcs is not yet implemented')

