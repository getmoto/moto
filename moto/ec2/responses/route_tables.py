from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class RouteTables(object):
    def associate_route_table(self):
        return NotImplemented

    def create_route(self):
        return NotImplemented

    def create_route_table(self):
        return NotImplemented

    def delete_route(self):
        return NotImplemented

    def delete_route_table(self):
        return NotImplemented

    def describe_route_tables(self):
        return NotImplemented

    def disassociate_route_table(self):
        return NotImplemented

    def replace_route(self):
        return NotImplemented

    def replace_route_table_association(self):
        return NotImplemented

