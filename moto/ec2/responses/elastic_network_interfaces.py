from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ElasticNetworkInterfaces(object):
    def attach_network_interface(self):
        return NotImplemented

    def create_network_interface(self):
        return NotImplemented

    def delete_network_interface(self):
        return NotImplemented

    def describe_network_interface_attribute(self):
        return NotImplemented

    def describe_network_interfaces(self):
        return NotImplemented

    def detach_network_interface(self):
        return NotImplemented

    def modify_network_interface_attribute(self):
        return NotImplemented

    def reset_network_interface_attribute(self):
        return NotImplemented

