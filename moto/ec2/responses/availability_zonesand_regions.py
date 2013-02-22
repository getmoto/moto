from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class AvailabilityZonesandRegions(object):
    def describe_availability_zones(self):
        raise NotImplementedError('AvailabilityZonesandRegions.describe_availability_zones is not yet implemented')

    def describe_regions(self):
        raise NotImplementedError('AvailabilityZonesandRegions.describe_regions is not yet implemented')

