from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class PlacementGroups(object):
    def create_placement_group(self):
        raise NotImplementedError('PlacementGroups.create_placement_group is not yet implemented')

    def delete_placement_group(self):
        raise NotImplementedError('PlacementGroups.delete_placement_group is not yet implemented')

    def describe_placement_groups(self):
        raise NotImplementedError('PlacementGroups.describe_placement_groups is not yet implemented')
