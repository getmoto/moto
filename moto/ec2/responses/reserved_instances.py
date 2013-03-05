from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ReservedInstances(object):
    def cancel_reserved_instances_listing(self):
        raise NotImplementedError('ReservedInstances.cancel_reserved_instances_listing is not yet implemented')

    def create_reserved_instances_listing(self):
        raise NotImplementedError('ReservedInstances.create_reserved_instances_listing is not yet implemented')

    def describe_reserved_instances(self):
        raise NotImplementedError('ReservedInstances.describe_reserved_instances is not yet implemented')

    def describe_reserved_instances_listings(self):
        raise NotImplementedError('ReservedInstances.describe_reserved_instances_listings is not yet implemented')

    def describe_reserved_instances_offerings(self):
        raise NotImplementedError('ReservedInstances.describe_reserved_instances_offerings is not yet implemented')

    def purchase_reserved_instances_offering(self):
        raise NotImplementedError('ReservedInstances.purchase_reserved_instances_offering is not yet implemented')
