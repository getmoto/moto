from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class PlacementGroups(object):
    def create_placement_group(self):
        return NotImplemented

    def delete_placement_group(self):
        return NotImplemented

    def describe_placement_groups(self):
        return NotImplemented

