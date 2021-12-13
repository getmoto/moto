from __future__ import unicode_literals

from moto.compat import OrderedDict
from moto.core.utils import get_random_hex
from .base import BaseRDSBackend, BaseRDSModel
from .tag import TaggableRDSResource
from ..exceptions import DBSubnetGroupNotFound
from .. import utils


class DBSubnetGroup(TaggableRDSResource, BaseRDSModel):

    resource_type = "subgrp"

    def __init__(self, backend, subnet_name, description, subnets, tags=None):
        super(DBSubnetGroup, self).__init__(backend)
        self.db_subnet_group_name = subnet_name
        self.db_subnet_group_description = description
        self.subnet_group_status = "Complete"
        self._subnets = subnets
        self.vpc_id = self._subnets[0].vpc_id
        if tags:
            self.add_tags(tags)

    @property
    def resource_id(self):
        return self.db_subnet_group_name

    @property
    def db_subnet_group_arn(self):
        return self.arn

    @property
    def subnets(self):
        return [
            {
                "subnet_identifier": subnet.id,
                "subnet_availability_zone": {"name": subnet.availability_zone},
                "subnet_status": "Active",
            }
            for subnet in self._subnets
        ]

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        if "DBSubnetGroupName" not in properties:
            properties["DBSubnetGroupName"] = resource_name.lower() + get_random_hex(12)
        backend = cls.get_regional_backend(region_name)
        params = utils.parse_cf_properties("CreateDBSubnetGroup", properties)
        subnet_group = backend.create_db_subnet_group(**params)
        return subnet_group

    def delete(self):
        self.backend.delete_subnet_group(self.db_subnet_group_name)


class DBSubnetGroupBackend(BaseRDSBackend):
    def __init__(self):
        super(DBSubnetGroupBackend, self).__init__()
        self.db_subnet_groups = OrderedDict()

    def get_db_subnet_group(self, db_subnet_group_name):
        if db_subnet_group_name not in self.db_subnet_groups:
            raise DBSubnetGroupNotFound(db_subnet_group_name)
        return self.db_subnet_groups[db_subnet_group_name]

    def create_db_subnet_group(
        self,
        db_subnet_group_name,
        db_subnet_group_description,
        subnet_ids=None,
        tags=None,
    ):
        subnets = [self.ec2.get_subnet(subnet_id) for subnet_id in subnet_ids]
        subnet_group = DBSubnetGroup(
            self, db_subnet_group_name, db_subnet_group_description, subnets, tags
        )
        self.db_subnet_groups[db_subnet_group_name] = subnet_group
        return subnet_group

    def describe_db_subnet_groups(self, db_subnet_group_name=None):
        if db_subnet_group_name:
            return [self.get_db_subnet_group(db_subnet_group_name)]
        return self.db_subnet_groups.values()

    def delete_db_subnet_group(self, db_subnet_group_name):
        db_subnet_group = self.get_db_subnet_group(db_subnet_group_name)
        return self.db_subnet_groups.pop(db_subnet_group.resource_id)
