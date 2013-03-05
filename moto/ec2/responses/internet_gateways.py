from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class InternetGateways(object):
    def attach_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).attach_internet_gateway is not yet implemented')

    def create_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).create_internet_gateway is not yet implemented')

    def delete_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).delete_internet_gateway is not yet implemented')

    def describe_internet_gateways(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).describe_internet_gateways is not yet implemented')

    def detach_internet_gateway(self):
        raise NotImplementedError('InternetGateways(AmazonVPC).detach_internet_gateway is not yet implemented')
