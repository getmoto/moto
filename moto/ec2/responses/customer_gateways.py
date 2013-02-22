from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class CustomerGateways(object):
    def create_customer_gateway(self):
        return NotImplemented

    def delete_customer_gateway(self):
        return NotImplemented

    def describe_customer_gateways(self):
        return NotImplemented

