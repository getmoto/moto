from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ReservedInstances(object):
    def cancel_reserved_instances_listing(self):
        return NotImplemented

    def create_reserved_instances_listing(self):
        return NotImplemented

    def describe_reserved_instances(self):
        return NotImplemented

    def describe_reserved_instances_listings(self):
        return NotImplemented

    def describe_reserved_instances_offerings(self):
        return NotImplemented

    def purchase_reserved_instances_offering(self):
        return NotImplemented

