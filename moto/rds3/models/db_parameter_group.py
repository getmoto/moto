from __future__ import unicode_literals

from collections import defaultdict

from moto.compat import OrderedDict
from .base import BaseRDSBackend, BaseRDSModel
from .tag import TaggableRDSResource
from .. import utils
from ..exceptions import (
    DBParameterGroupNotFound,
    DBParameterGroupAlreadyExists,
    InvalidParameterValue,
)


class Parameter(object):
    def __init__(
        self,
        parameter_name,
        parameter_value,
        description="",
        apply_method="immediately",
        **kwargs
    ):
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.description = description
        self.apply_method = apply_method

    def update(self, attrs):
        self.__dict__.update(attrs)

    @property
    def resource_id(self):
        return self.parameter_name


class DBParameterGroup(TaggableRDSResource, BaseRDSModel):

    resource_type = "pg"

    def __init__(
        self,
        backend,
        db_parameter_group_name,
        description,
        db_parameter_group_family,
        tags=None,
    ):
        super(DBParameterGroup, self).__init__(backend)
        self.db_parameter_group_name = db_parameter_group_name
        self.description = description
        self.db_parameter_group_family = db_parameter_group_family
        if tags:
            self.add_tags(tags)
        self._parameters = defaultdict(dict)

    @property
    def resource_id(self):
        return self.db_parameter_group_name

    @property
    def name(self):
        return self.resource_id

    @property
    def db_parameter_group_arn(self):
        return self.arn

    @property
    def parameters(self):
        return self._parameters.values()

    def update_parameters(self, new_parameters):
        for new_parameter in new_parameters:
            param_name = new_parameter["parameter_name"]
            if param_name in self._parameters:
                self._parameters[param_name].update(new_parameter)
            else:
                self._parameters[param_name] = Parameter(**new_parameter)

    def delete(self):
        self.backend.delete_db_parameter_group(self.identifier)

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        if "DBParameterGroupName" not in properties:
            properties["DBParameterGroupName"] = resource_name.lower()
        backend = cls.get_regional_backend(region_name)
        params = utils.parse_cf_properties("CreateDBParameterGroup", properties)
        db_parameter_group = backend.create_db_parameter_group(**params)
        db_parameter_group_parameters = []
        for db_parameter, db_parameter_value in properties.get(
            "Parameters", {}
        ).items():
            db_parameter_group_parameters.append(
                {"parameter_name": db_parameter, "parameter_value": db_parameter_value,}
            )
        db_parameter_group.update_parameters(db_parameter_group_parameters)
        return db_parameter_group


class DBParameterGroupBackend(BaseRDSBackend):
    def __init__(self):
        super(DBParameterGroupBackend, self).__init__()
        self.db_parameter_groups = OrderedDict()
        for item in utils.default_db_parameter_groups:
            group = DBParameterGroup(
                backend=self,
                db_parameter_group_name=item["DBParameterGroupName"],
                db_parameter_group_family=item["DBParameterGroupFamily"],
                description=item["Description"],
            )
            self.db_parameter_groups[group.resource_id] = group

    def get_db_parameter_group(self, db_parameter_group_name):
        if db_parameter_group_name in self.db_parameter_groups:
            return self.db_parameter_groups[db_parameter_group_name]
        raise DBParameterGroupNotFound(db_parameter_group_name)

    def delete_db_parameter_group(self, db_parameter_group_name):
        db_parameter_group = self.get_db_parameter_group(db_parameter_group_name)
        return self.db_parameter_groups.pop(db_parameter_group.resource_id)

    def create_db_parameter_group(
        self,
        db_parameter_group_name,
        db_parameter_group_family,
        description=None,
        tags=None,
    ):
        if db_parameter_group_name in self.db_parameter_groups:
            raise DBParameterGroupAlreadyExists(db_parameter_group_name)
        if not description:
            raise InvalidParameterValue(
                "The parameter Description must be provided and must not be blank."
            )
        db_parameter_group = DBParameterGroup(
            backend=self,
            db_parameter_group_name=db_parameter_group_name,
            db_parameter_group_family=db_parameter_group_family,
            description=description,
            tags=tags,
        )
        self.db_parameter_groups[db_parameter_group_name] = db_parameter_group
        return db_parameter_group

    def describe_db_parameter_groups(self, db_parameter_group_name=None, **kwargs):
        if db_parameter_group_name:
            return [self.get_db_parameter_group(db_parameter_group_name)]
        return self.db_parameter_groups.values()

    def modify_db_parameter_group(self, db_parameter_group_name, parameters):
        db_parameter_group = self.get_db_parameter_group(db_parameter_group_name)
        db_parameter_group.update_parameters(parameters)
        return db_parameter_group_name

    def describe_db_parameters(self, db_parameter_group_name=None, **kwargs):
        db_parameter_group = self.get_db_parameter_group(db_parameter_group_name)
        return db_parameter_group.parameters
