from __future__ import unicode_literals

from .base import BaseRDSBackend, BaseRDSModel
from .tag import TaggableRDSResource
from moto.compat import OrderedDict
from collections import defaultdict
from ..exceptions import (
    DBClusterParameterGroupNotFound,
    InvalidParameterValue,
    DBClusterParameterGroupAlreadyExists,
)
from .. import utils


# TODO: Merge this with DBParameterGroup
# Just subclass and have backend methods set a cluster flag to distinguish
class DBClusterParameterGroup(TaggableRDSResource, BaseRDSModel):

    resource_type = "cluster-pg"

    def __init__(
        self,
        backend,
        db_cluster_parameter_group_name,
        description,
        db_parameter_group_family,
        tags=None,
    ):
        super(DBClusterParameterGroup, self).__init__(backend)
        self.db_cluster_parameter_group_name = db_cluster_parameter_group_name
        self.description = description
        self.db_parameter_group_family = db_parameter_group_family
        if tags:
            self.add_tags(tags)
        self.parameters = defaultdict(dict)

    @property
    def resource_id(self):
        return self.db_cluster_parameter_group_name

    @property
    def name(self):
        return self.db_cluster_parameter_group_name

    @property
    def db_cluster_parameter_group_arn(self):
        return self.arn

    def update_parameters(self, new_parameters):
        for new_parameter in new_parameters:
            parameter = self.parameters[new_parameter["ParameterName"]]
            parameter.update(new_parameter)

    def delete(self):
        # TODO: Only used for Cloud Formation?
        self.backend.delete_db_cluster_parameter_group(self.identifier)


class DBClusterParameterGroupBackend(BaseRDSBackend):
    def __init__(self):
        super(DBClusterParameterGroupBackend, self).__init__()
        self.db_cluster_parameter_groups = OrderedDict()
        for item in utils.default_db_cluster_parameter_groups:
            group = DBClusterParameterGroup(
                backend=self,
                db_cluster_parameter_group_name=item["DBClusterParameterGroupName"],
                db_parameter_group_family=item["DBParameterGroupFamily"],
                description=item["Description"],
            )
            self.db_cluster_parameter_groups[group.resource_id] = group

    def get_db_cluster_parameter_group(self, db_cluster_parameter_group_name):
        if db_cluster_parameter_group_name in self.db_cluster_parameter_groups:
            return self.db_cluster_parameter_groups[db_cluster_parameter_group_name]
        raise DBClusterParameterGroupNotFound(db_cluster_parameter_group_name)

    def create_db_cluster_parameter_group(
        self,
        db_cluster_parameter_group_name=None,
        db_parameter_group_family=None,
        description="",
        **kwargs
    ):
        if db_cluster_parameter_group_name in self.db_cluster_parameter_groups:
            raise DBClusterParameterGroupAlreadyExists(db_cluster_parameter_group_name)
        if not description:
            raise InvalidParameterValue(
                "The parameter Description must be provided and must not be blank."
            )
        if not db_parameter_group_family:
            raise InvalidParameterValue(
                "The parameter DBParameterGroupName must be provided and must not be blank."
            )
        db_cluster_parameter_group = DBClusterParameterGroup(
            backend=self,
            db_cluster_parameter_group_name=db_cluster_parameter_group_name,
            db_parameter_group_family=db_parameter_group_family,
            description=description,
            **kwargs
        )
        self.db_cluster_parameter_groups[
            db_cluster_parameter_group_name
        ] = db_cluster_parameter_group
        return db_cluster_parameter_group

    def delete_db_cluster_parameter_group(self, db_cluster_parameter_group_name):
        param_group = self.get_db_cluster_parameter_group(
            db_cluster_parameter_group_name
        )
        return self.db_cluster_parameter_groups.pop(param_group.resource_id)

    def describe_db_cluster_parameter_groups(
        self, db_cluster_parameter_group_name=None, **kwargs
    ):
        if db_cluster_parameter_group_name:
            return [
                self.get_db_cluster_parameter_group(db_cluster_parameter_group_name)
            ]
        return self.db_cluster_parameter_groups.values()
