from __future__ import unicode_literals

import datetime

from moto.compat import OrderedDict
from .base import BaseRDSBackend, BaseRDSModel
from .event import EventMixin
from .tag import TaggableRDSResource
from .. import utils
from ..exceptions import (
    DBClusterNotFound,
    DBClusterToBeDeletedHasActiveMembers,
    InvalidAvailabilityZones,
    InvalidParameterValue,
)


class DBCluster(TaggableRDSResource, EventMixin, BaseRDSModel):

    resource_type = "cluster"

    def __init__(
        self,
        backend,
        identifier,
        engine,
        engine_version,
        master_username,
        master_user_password,
        availability_zones,
        backup_retention_period=1,
        character_set_name=None,
        copy_tags_to_snapshot=False,
        database_name=None,
        db_cluster_parameter_group_name=None,
        db_subnet_group=None,
        port=123,
        preferred_backup_window=None,
        storage_encrypted=False,
        tags=None,
        vpc_security_group_ids=None,
        **kwargs
    ):
        super(DBCluster, self).__init__(backend)
        self.allocated_storage = 1
        self.availability_zones = availability_zones
        self.backup_retention_period = backup_retention_period
        self.character_set_name = character_set_name
        self.copy_tags_to_snapshot = copy_tags_to_snapshot
        self.database_name = database_name
        self.db_cluster_identifier = identifier
        self.db_cluster_parameter_group_name = db_cluster_parameter_group_name
        self._db_subnet_group = db_subnet_group
        self.engine = engine
        self.engine_version = engine_version
        self.master_user_password = master_user_password
        self.master_username = master_username
        self.preferred_backup_window = preferred_backup_window or "05:30-06:00"
        self.port = port
        self.storage_type = "aurora"
        self.storage_encrypted = storage_encrypted
        if self.storage_encrypted:
            self.kms_key_id = kwargs.get("kms_key_id", "default_kms_key_id")
        else:
            self.kms_key_id = kwargs.get("kms_key_id")
        self.vpc_security_group_ids = vpc_security_group_ids or []
        if tags:
            self.add_tags(tags)

    @property
    def resource_id(self):
        return self.db_cluster_identifier

    @property
    def db_subnet_group(self):
        return self._db_subnet_group.resource_id

    @property
    def db_cluster_parameter_group(self):
        return self.db_cluster_parameter_group_name

    @property
    def endpoint(self):
        return "{}.cluster-xxxxxxxx.{}.rds.amazonaws.com".format(
            self.resource_id, self.backend.region
        )

    @property
    def reader_endpoint(self):
        return self.endpoint.replace("cluster-", "cluster-ro-")

    @property
    def multi_az(self):
        availability_zones = list(
            set([instance.availability_zone for instance in self._members])
        )
        return True if len(availability_zones) > 1 else False

    @property
    def _members(self):
        return [
            db_instance
            for db_instance in self.backend.db_instances.values()
            if db_instance.db_cluster_identifier == self.resource_id
        ]

    @property
    def writer(self):
        return next(
            (
                db_instance
                for db_instance in self._members
                if db_instance.is_cluster_writer
            ),
            None,
        )

    @writer.setter
    def writer(self, db_instance):
        db_instance.is_cluster_writer = True

    @property
    def members(self):
        self.designate_writer()
        return self._members

    @property
    def db_cluster_arn(self):
        return self.arn

    @property
    def cluster_create_time(self):
        return self.created

    @property
    def status(self):
        return "available"

    @property
    def db_cluster_members(self):
        return [
            {
                "db_cluster_parameter_group_status": "in-sync",
                "db_instance_identifier": member.resource_id,
                "is_cluster_writer": member.is_cluster_writer,
                "promotion_tier": member.promotion_tier,
            }
            for member in self.members
        ]

    @property
    def vpc_security_groups(self):
        return [
            {"status": "active", "vpc_security_group_id": group_id}
            for group_id in self.vpc_security_group_ids
        ]

    def designate_writer(self):
        if self.writer or not self._members:
            return
        if len(self._members) == 1:
            self.writer = self._members[0]
        else:
            promotion_list = sorted(self._members, key=lambda x: x.promotion_tier)
            self.writer = promotion_list[0]

    def delete(self):
        # I think this only for cloud formation...
        self.backend.delete_database(self.resource_id)

    def failover(self, target_member_identifier):
        if target_member_identifier not in [
            member.resource_id for member in self.members
        ]:
            raise InvalidParameterValue(
                "Cannot find target instance :{}.".format(target_member_identifier)
            )
        target_instance = self.backend.get_db_instance(target_member_identifier)
        self.writer.is_cluster_writer = False
        self.writer = target_instance

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if value:
                setattr(self, key, value)


class DBClusterBackend(BaseRDSBackend):
    def __init__(self):
        super(DBClusterBackend, self).__init__()
        self.db_clusters = OrderedDict()

    def get_db_cluster(self, db_cluster_identifier):
        if db_cluster_identifier in self.db_clusters:
            return self.db_clusters[db_cluster_identifier]
        raise DBClusterNotFound(db_cluster_identifier)

    def create_db_cluster(self, db_cluster_identifier, **kwargs):
        cluster_kwargs = self._validate_create_cluster_args(kwargs)
        cluster = DBCluster(self, db_cluster_identifier, **cluster_kwargs)
        self.db_clusters[db_cluster_identifier] = cluster
        snapshot_id = "{}-{}".format(
            db_cluster_identifier, datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
        )
        self.create_db_cluster_snapshot(
            db_cluster_identifier, snapshot_id, snapshot_type="automated"
        )
        return cluster

    def delete_db_cluster(
        self,
        db_cluster_identifier,
        skip_final_snapshot=False,
        final_db_snapshot_identifier=None,
    ):
        cluster = self.get_db_cluster(db_cluster_identifier)
        if cluster.members:
            raise DBClusterToBeDeletedHasActiveMembers()
        cluster.delete_events()
        return self.db_clusters.pop(db_cluster_identifier)

    def describe_db_clusters(self, db_cluster_identifier=None, **kwargs):
        if db_cluster_identifier:
            return [self.get_db_cluster(db_cluster_identifier)]
        return self.db_clusters.values()

    def failover_db_cluster(self, db_cluster_identifier, target_db_instance_identifier):
        cluster = self.get_db_cluster(db_cluster_identifier)
        cluster.failover(target_db_instance_identifier)

    def modify_db_cluster(
        self, db_cluster_identifier, new_db_cluster_identifier=None, **kwargs
    ):
        cluster = self.get_db_cluster(db_cluster_identifier)
        if new_db_cluster_identifier is not None:
            del self.db_clusters[db_cluster_identifier]
            db_cluster_identifier = kwargs[
                "db_cluster_identifier"
            ] = new_db_cluster_identifier
            self.db_clusters[db_cluster_identifier] = cluster
        cluster.update(**kwargs)
        return cluster

    def restore_db_cluster_from_snapshot(
        self, db_cluster_identifier, snapshot_identifier, **kwargs
    ):
        # TODO: Snapshot can be name or arn for cluster snapshot or arn for db_instance snapshot.
        snapshot = self.get_db_cluster_snapshot(snapshot_identifier)
        cluster_args = dict(**snapshot.cluster.__dict__)
        # AWS restores the cluster with most of the original configuration,
        # but with the default security group.
        cluster_args.pop("vpc_security_group_ids", None)
        # Use our backend and update with any user-provided parameters.
        cluster_args.update(backend=self, **kwargs)
        cluster_args = self._validate_create_cluster_args(cluster_args)
        cluster = DBCluster(identifier=db_cluster_identifier, **cluster_args)
        self.db_clusters[db_cluster_identifier] = cluster
        return cluster

    def restore_db_cluster_to_point_in_time(
        self, db_cluster_identifier, source_db_cluster_identifier, **kwargs
    ):
        source = self.get_db_cluster(source_db_cluster_identifier)
        cluster_args = dict(**source.__dict__)
        # AWS restores the cluster with most of the original configuration,
        # but with the default security group.
        cluster_args.pop("vpc_security_group_ids", None)
        # Use our backend and update with any user-provided parameters.
        cluster_args.update(backend=self, **kwargs)
        cluster_args = self._validate_create_cluster_args(cluster_args)
        cluster = DBCluster(identifier=db_cluster_identifier, **cluster_args)
        self.db_clusters[db_cluster_identifier] = cluster
        return cluster

    def _validate_create_cluster_args(self, kwargs):
        engine = kwargs.get("engine")
        if engine not in utils.VALID_DB_CLUSTER_ENGINES:
            raise InvalidParameterValue("Invalid DB engine")
        if "engine_version" not in kwargs:
            kwargs["engine_version"] = utils.default_engine_version(engine)
        if kwargs["engine_version"] not in utils.valid_engine_versions(engine):
            msg = "Cannot find version {} for {}".format(
                kwargs["engine_version"], engine
            )
            raise InvalidParameterValue(msg)
        if "db_cluster_parameter_group_name" not in kwargs:
            kwargs[
                "db_cluster_parameter_group_name"
            ] = utils.default_db_cluster_parameter_group_name(engine)
        # This will raise an exception if the param group doesn't exist.
        self.get_db_cluster_parameter_group(kwargs["db_cluster_parameter_group_name"])
        availability_zones = [
            zone.name for zone in self.ec2.describe_availability_zones()
        ]
        if "availability_zones" not in kwargs:
            kwargs["availability_zones"] = availability_zones
        if not set(kwargs["availability_zones"]).issubset(set(availability_zones)):
            invalid_zones = set(kwargs["availability_zones"]) - set(availability_zones)
            raise InvalidAvailabilityZones(list(invalid_zones))
        if "db_subnet_group_name" in kwargs:
            kwargs["db_subnet_group"] = self.get_db_subnet_group(
                kwargs["db_subnet_group_name"]
            )
        if "port" not in kwargs:
            kwargs["port"] = utils.default_engine_port(engine)
        return kwargs
