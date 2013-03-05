from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class CustomerGateways(object):
    def create_customer_gateway(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).create_customer_gateway is not yet implemented')

    def delete_customer_gateway(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).delete_customer_gateway is not yet implemented')

    def describe_customer_gateways(self):
        raise NotImplementedError('CustomerGateways(AmazonVPC).describe_customer_gateways is not yet implemented')
