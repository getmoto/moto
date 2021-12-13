from __future__ import unicode_literals

from moto.compat import OrderedDict
from moto.core.utils import get_random_hex
from .base import BaseRDSBackend, BaseRDSModel
from .tag import TaggableRDSResource
from ..exceptions import DBSecurityGroupNotFound
from ..models.base import ACCOUNT_ID
from .. import utils


class DBSecurityGroup(TaggableRDSResource, BaseRDSModel):

    resource_type = "secgrp"

    def __init__(
        self, backend, db_security_group_name, db_security_group_description, tags=None
    ):
        super(DBSecurityGroup, self).__init__(backend)
        self.db_security_group_name = db_security_group_name
        self.db_security_group_description = db_security_group_description
        self._ip_ranges = []
        self._ec2_security_groups = []
        if tags:
            self.add_tags(tags)
        self.owner_id = ACCOUNT_ID
        self.vpc_id = None

    @property
    def resource_id(self):
        return self.db_security_group_name

    @property
    def db_security_group_arn(self):
        return self.arn

    @property
    def ec2_security_groups(self):
        return [
            {
                "status": "authorized",
                "ec2_security_group_name": security_group.name,
                "ec2_security_group_id": security_group.id,
                "ec2_security_group_owner_id": security_group.owner_id,
            }
            for security_group in self._ec2_security_groups
        ]

    @property
    def ip_ranges(self):
        return [
            {"status": "authorized", "cidrip": ip_range} for ip_range in self._ip_ranges
        ]

    def authorize_cidr(self, cidr_ip):
        self._ip_ranges.append(cidr_ip)

    def authorize_security_group(self, security_group):
        self._ec2_security_groups.append(security_group)

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        if "DBSecurityGroupName" not in properties:
            properties["DBSecurityGroupName"] = resource_name.lower() + get_random_hex(
                12
            )
        backend = cls.get_regional_backend(region_name)
        params = utils.parse_cf_properties("CreateDBSecurityGroup", properties)
        security_group = backend.create_db_security_group(**params)
        ec2_backend = cls.get_regional_ec2_backend(region_name)
        for security_group_ingress in properties.get("DBSecurityGroupIngress", []):
            for ingress_type, ingress_value in security_group_ingress.items():
                if ingress_type == "CIDRIP":
                    security_group.authorize_cidr(ingress_value)
                elif ingress_type == "EC2SecurityGroupName":
                    subnet = ec2_backend.get_security_group_from_name(ingress_value)
                    security_group.authorize_security_group(subnet)
                elif ingress_type == "EC2SecurityGroupId":
                    subnet = ec2_backend.get_security_group_from_id(ingress_value)
                    security_group.authorize_security_group(subnet)
        return security_group

    def delete(self):
        self.backend.delete_security_group(self.group_name)


class DBSecurityGroupBackend(BaseRDSBackend):
    def __init__(self):
        super(DBSecurityGroupBackend, self).__init__()
        self.db_security_groups = OrderedDict()

    def get_db_security_group(self, db_security_group_name):
        if db_security_group_name in self.db_security_groups:
            return self.db_security_groups[db_security_group_name]
        raise DBSecurityGroupNotFound(db_security_group_name)

    def create_db_security_group(
        self, db_security_group_name, db_security_group_description, tags=None
    ):
        security_group = DBSecurityGroup(
            self, db_security_group_name, db_security_group_description, tags
        )
        self.db_security_groups[db_security_group_name] = security_group
        return security_group

    def describe_db_security_groups(self, db_security_group_name=None, **kwargs):
        if db_security_group_name:
            return [self.get_db_security_group(db_security_group_name)]
        return self.db_security_groups.values()

    def delete_db_security_group(self, db_security_group_name):
        security_group = self.get_db_security_group(db_security_group_name)
        return self.db_security_groups.pop(security_group.resource_id)

    def authorize_db_security_group_ingress(self, db_security_group_name, cidrip):
        security_group = self.get_db_security_group(db_security_group_name)
        security_group.authorize_cidr(cidrip)
        return security_group
