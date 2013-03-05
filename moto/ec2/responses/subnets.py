from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class Subnets(object):
    def create_subnet(self):
        raise NotImplementedError('Subnets(AmazonVPC).create_subnet is not yet implemented')

    def delete_subnet(self):
        raise NotImplementedError('Subnets(AmazonVPC).delete_subnet is not yet implemented')

    def describe_subnets(self):
        raise NotImplementedError('Subnets(AmazonVPC).describe_subnets is not yet implemented')
