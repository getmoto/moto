from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ElasticNetworkInterfaces(object):
    def attach_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).attach_network_interface is not yet implemented')

    def create_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).create_network_interface is not yet implemented')

    def delete_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).delete_network_interface is not yet implemented')

    def describe_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).describe_network_interface_attribute is not yet implemented')

    def describe_network_interfaces(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).describe_network_interfaces is not yet implemented')

    def detach_network_interface(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).detach_network_interface is not yet implemented')

    def modify_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).modify_network_interface_attribute is not yet implemented')

    def reset_network_interface_attribute(self):
        raise NotImplementedError('ElasticNetworkInterfaces(AmazonVPC).reset_network_interface_attribute is not yet implemented')
