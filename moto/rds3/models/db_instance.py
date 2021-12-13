from __future__ import unicode_literals

import datetime
import random
from re import compile as re_compile

from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
from moto.compat import OrderedDict
from moto.core.utils import get_random_hex
from ..exceptions import (
    DBInstanceAlreadyExists,
    DBInstanceNotFound,
    InvalidDBClusterStateFault,
    InvalidDBInstanceState,
    InvalidAvailabilityZones,
    InvalidParameterValue,
    InvalidParameterCombination,
)
from .base import BaseRDSBackend, BaseRDSModel
from .event import EventMixin
from .log import LogFileManager
from .tag import TaggableRDSResource
from .. import utils


class DBInstance(TaggableRDSResource, EventMixin, BaseRDSModel):

    event_source_type = "db-instance"
    resource_type = "db"

    def __init__(
        self,
        backend,
        identifier,
        availability_zone,
        db_instance_class,
        engine,
        engine_version,
        option_group_name,
        port,
        allocated_storage=10,
        backup_retention_period=1,
        character_set_name=None,
        auto_minor_version_upgrade=True,
        db_name=None,
        db_security_groups=None,
        db_subnet_group=None,
        db_cluster_identifier=None,
        db_parameter_group_name=None,
        copy_tags_to_snapshot=False,
        iops=None,
        master_username=None,
        master_user_password=None,
        max_allocated_storage=None,
        multi_az=False,
        license_model="general-public-license",
        preferred_backup_window="13:14-13:44",
        preferred_maintenance_window="wed:06:38-wed:07:08",
        promotion_tier=1,
        publicly_accessible=None,
        source_db_instance_identifier=None,
        storage_type="standard",
        storage_encrypted=False,
        tags=None,
        vpc_security_group_ids=None,
        **kwargs
    ):
        super(DBInstance, self).__init__(backend)

        self.db_instance_identifier = identifier
        self.status = "available"

        self.engine = engine

        self.port = port
        self.db_name = db_name

        self.iops = iops

        self.auto_minor_version_upgrade = auto_minor_version_upgrade

        self.preferred_maintenance_window = preferred_maintenance_window
        self.promotion_tier = promotion_tier
        self.read_replica_source_db_instance_identifier = source_db_instance_identifier
        self.db_instance_class = db_instance_class

        self.publicly_accessible = publicly_accessible
        if self.publicly_accessible is None:
            self.publicly_accessible = False if db_subnet_group else True

        self.availability_zone = availability_zone

        self.multi_az = multi_az

        self.db_subnet_group = db_subnet_group

        self._db_security_groups = db_security_groups or []

        if db_parameter_group_name is None:
            self.db_parameter_group_name = utils.default_db_parameter_group_name(
                self.engine, engine_version
            )
        else:
            self.db_parameter_group_name = db_parameter_group_name

        self._db_parameter_groups = [
            {"name": self.db_parameter_group_name, "status": "in-sync"}
        ]

        self.license_model = license_model

        self.option_group_name = option_group_name
        self._option_groups = [{"name": self.option_group_name, "status": "in-sync"}]

        self.copy_tags_to_snapshot = copy_tags_to_snapshot
        if tags:
            self.add_tags(tags)

        self.log_file_manager = LogFileManager(self.engine)

        self.db_cluster_identifier = db_cluster_identifier
        if self.db_cluster_identifier is None:
            self.allocated_storage = allocated_storage
            if max_allocated_storage is not None:
                self.max_allocated_storage = max_allocated_storage
            else:
                self.max_allocated_storage = self.allocated_storage
            self.storage_type = "io1" if self.iops else storage_type
            self.storage_encrypted = storage_encrypted
            if self.storage_encrypted:
                self.kms_key_id = kwargs.get("kms_key_id", "default_kms_key_id")
            else:
                self.kms_key_id = kwargs.get("kms_key_id")
            self.backup_retention_period = backup_retention_period
            self.character_set_name = character_set_name
            self.engine_version = engine_version
            self.master_username = master_username
            self.master_user_password = master_user_password
            self.preferred_backup_window = preferred_backup_window
            self.vpc_security_group_ids = vpc_security_group_ids or []
        # else:
        # TODO: Raise errors if any of these values are passed to clustered instance?

    @property
    def resource_id(self):
        return self.db_instance_identifier

    @property
    def db_instance_status(self):
        return self.status

    @property
    def db_instance_arn(self):
        return self.arn

    @property
    def db_security_groups(self):
        return [
            {"status": "active", "db_security_group_name": security_group}
            for security_group in self._db_security_groups
        ]

    @db_security_groups.setter
    def db_security_groups(self, value):
        self._db_security_groups = value

    @property
    def db_parameter_groups(self):
        return [
            {
                "parameter_apply_status": db_parameter_group["status"],
                "db_parameter_group_name": db_parameter_group["name"],
            }
            for db_parameter_group in self._db_parameter_groups
        ]

    @property
    def option_group_memberships(self):
        return [
            {
                "status": option_group["status"],
                "option_group_name": option_group["name"],
            }
            for option_group in self._option_groups
        ]

    @property
    def endpoint(self):
        return {"address": self.address, "port": self.port}

    @property
    def read_replica_db_instance_identifiers(self):
        return [replica for replica in self.read_replicas]

    @property
    def status_infos(self):
        if self.is_replica:
            return [
                {
                    "status_type": "read replication",
                    "status": "replicating",
                    "normal": True,
                    "message": None,
                }
            ]
        else:
            return None

    @property
    def vpc_security_groups(self):
        return [
            {"status": "active", "vpc_security_group_id": group_id}
            for group_id in self.vpc_security_group_ids
        ]

    @property
    def max_allocated_storage(self):
        return (
            self._max_allocated_storage
            if self._max_allocated_storage != self.allocated_storage
            else None
        )

    @max_allocated_storage.setter
    def max_allocated_storage(self, value):
        if value < self.allocated_storage:
            raise InvalidParameterCombination(
                "Max storage size must be greater than storage size"
            )
        self._max_allocated_storage = value

    @property
    def address(self):
        return "{0}.aaaaaaaaaa.{1}.rds.amazonaws.com".format(
            self.resource_id, self.backend.region
        )

    # Commenting this out for now because it breaks the stupid GraphQL snapshottests in the RDS Broker...
    # @property
    # def instance_create_time(self):
    #     return self.created
    #
    # @property
    # def latest_restorable_time(self):
    #     from moto.core.utils import iso_8601_datetime_with_milliseconds
    #     return iso_8601_datetime_with_milliseconds(datetime.datetime.now())

    def update(self, db_kwargs):
        # TODO: This is all horrible.  Must fix.
        if "max_allocated_storage" in db_kwargs:
            self.max_allocated_storage = db_kwargs.get("max_allocated_storage")
        # TODO: This is all horrible.  Must fix.
        if db_kwargs.get("db_parameter_group_name"):
            db_parameter_group_name = db_kwargs.pop("db_parameter_group_name")
            self._db_parameter_groups = [
                {"name": db_parameter_group_name, "status": "pending-reboot"}
            ]
        # TODO: This is all horrible.  Must fix.
        if db_kwargs.get("option_group_name"):
            option_group_name = db_kwargs.pop("option_group_name")
            self._option_groups = [{"name": option_group_name, "status": "in-sync"}]
        # Hack: get instance id before tags, because tags depend on resource_id for arn...
        if "db_instance_identifier" in db_kwargs:
            self.db_instance_identifier = db_kwargs.pop("db_instance_identifier")
        self.add_tags(db_kwargs.pop("tags", []))
        for key, value in db_kwargs.items():
            if value:
                setattr(self, key, value)

    def reboot(self):
        for param_group in self._db_parameter_groups:
            if param_group["status"] == "pending-reboot":
                param_group["status"] = "in-sync"

    def get_cfn_attribute(self, attribute_name):
        if attribute_name == "Endpoint.Address":
            return self.address
        elif attribute_name == "Endpoint.Port":
            return self.port
        raise UnformattedGetAttTemplateException()

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        if "DBInstanceIdentifier" not in properties:
            properties["DBInstanceIdentifier"] = resource_name.lower() + get_random_hex(
                12
            )
        backend = cls.get_regional_backend(region_name)
        if "SourceDBInstanceIdentifier" in properties:
            params = utils.parse_cf_properties(
                "CreateDBInstanceReadReplica", properties
            )
            db_instance = backend.create_db_instance_read_replica(**params)
        else:
            params = utils.parse_cf_properties("CreateDBInstance", properties)
            db_instance = backend.create_db_instance(**params)
        return db_instance

    def delete(self):
        # Only for CloudFormation?
        self.backend.delete_database(self.resource_id)

    @property
    def is_replica(self):
        return self.read_replica_source_db_instance_identifier is not None

    @property
    def read_replicas(self):
        replicas = []
        from . import rds3_backends

        for backend in rds3_backends.values():
            for db_instance in backend.db_instances.values():
                if backend.region == self.backend.region:
                    if (
                        db_instance.read_replica_source_db_instance_identifier
                        == self.resource_id
                    ):
                        replicas.append(db_instance.resource_id)
                else:
                    if (
                        db_instance.read_replica_source_db_instance_identifier
                        == self.arn
                    ):
                        replicas.append(db_instance.arn)
        return replicas


class ClusteredDBInstance(DBInstance):
    def __init__(self, backend, db_instance_identifier, **kwargs):
        super(ClusteredDBInstance, self).__init__(
            backend, db_instance_identifier, **kwargs
        )
        cluster_id = kwargs.get("db_cluster_identifier")
        self.cluster = self.backend.get_db_cluster(cluster_id)
        self.is_cluster_writer = True if not self.cluster.members else False

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if hasattr(self.cluster, name):
            return getattr(self.cluster, name)
        return super(ClusteredDBInstance, self).__getattr__(name)

    # TODO: Need to understand better how this works with Aurora instances.
    # According to the boto3 documentation, `db_name` is valid:
    # "The name of the database to create when the primary instance
    # of the DB cluster is created. If this parameter isn't specified,
    # no database is created in the DB instance."
    # So does that mean the cluster.database_name and the instance.db_name
    # can differ?
    @property
    def db_name(self):
        return self._db_name or self.cluster.database_name

    @db_name.setter
    def db_name(self, value):
        self._db_name = value


class DBInstanceBackend(BaseRDSBackend):
    def __init__(self):
        super(DBInstanceBackend, self).__init__()
        self.db_instances = OrderedDict()
        self.arn_regex = re_compile(
            r"^arn:aws:rds:.*:[0-9]*:(db|es|og|pg|ri|secgrp|snapshot|subgrp):.*$"
        )

    def get_db_instance(self, db_instance_identifier):
        if db_instance_identifier not in self.db_instances:
            raise DBInstanceNotFound(db_instance_identifier)
        return self.db_instances[db_instance_identifier]

    def _backup_db_instance(self, db_instance):
        # TODO: Make this method on DBInstance?
        db_instance.add_event("DB_INSTANCE_BACKUP_START")
        time_stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d-%H-%M")
        snapshot_id = "rds:{}-{}".format(db_instance.resource_id, time_stamp)
        self.create_db_snapshot(
            db_instance.resource_id, snapshot_id, snapshot_type="automated"
        )
        db_instance.add_event("DB_INSTANCE_BACKUP_FINISH")

    def create_db_instance(self, db_instance_identifier, **kwargs):
        if db_instance_identifier in self.db_instances:
            raise DBInstanceAlreadyExists(db_instance_identifier)
        instance_kwargs = self._validate_create_instance_args(kwargs)
        if "db_cluster_identifier" in instance_kwargs:
            db_instance = ClusteredDBInstance(
                self, db_instance_identifier, **instance_kwargs
            )
        else:
            db_instance = DBInstance(self, db_instance_identifier, **instance_kwargs)
        self.db_instances[db_instance_identifier] = db_instance
        db_instance.add_event("DB_INSTANCE_CREATE")
        # snapshot_id = '{}-{}'.format(db_instance_identifier, datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
        # self.create_db_snapshot(db_instance_identifier, snapshot_id, snapshot_type='automated')
        self._backup_db_instance(db_instance)
        return db_instance

    def restore_db_instance_from_db_snapshot(
        self, db_instance_identifier, db_snapshot_identifier, **kwargs
    ):
        snapshot = self.get_db_snapshot(db_snapshot_identifier)
        db_args = dict(**snapshot.db_instance.__dict__)
        # AWS restores the database with most of the original configuration,
        # but with the default security/parameter group.
        params_to_remove = [
            "vpc_security_group_ids",
            "db_security_groups",
            "db_parameter_group_name",
        ]
        for param in params_to_remove:
            db_args.pop(param, None)
        # Use our backend and update with any user-provided parameters.
        db_args.update(backend=self, **kwargs)
        db_args = self._validate_create_instance_args(db_args)
        db_instance = DBInstance(identifier=db_instance_identifier, **db_args)
        self.db_instances[db_instance_identifier] = db_instance
        return db_instance

    def restore_db_instance_to_point_in_time(
        self, source_db_instance_identifier, target_db_instance_identifier, **kwargs
    ):
        source = self.get_db_instance(source_db_instance_identifier)
        db_args = dict(**source.__dict__)
        # AWS restores the database with most of the original configuration,
        # but with the default security/parameter group.
        attrs_to_remove = [
            "vpc_security_group_ids",
            "db_security_groups",
            "db_parameter_group_name",
        ]
        for attr in attrs_to_remove:
            db_args.pop(attr, None)
        # Use our backend and update with any user-provided parameters.
        db_args.update(backend=self, **kwargs)
        db_args = self._validate_create_instance_args(db_args)
        db_instance = DBInstance(identifier=target_db_instance_identifier, **db_args)
        self.db_instances[target_db_instance_identifier] = db_instance
        return db_instance

    def create_db_instance_read_replica(
        self,
        db_instance_identifier,
        source_db_instance_identifier,
        multi_az=False,
        **kwargs
    ):
        source_db_instance = self.find_db_from_id(source_db_instance_identifier)
        db_args = dict(**source_db_instance.__dict__)
        if source_db_instance.region != self.region or multi_az:
            db_args.pop("availability_zone", None)
        # Use our backend and update with any user-provided parameters.
        db_args.update(backend=self, multi_az=multi_az, **kwargs)
        db_args = self._validate_create_instance_args(db_args)
        db_instance = DBInstance(
            identifier=db_instance_identifier,
            source_db_instance_identifier=source_db_instance_identifier,
            **db_args
        )
        self.db_instances[db_instance_identifier] = db_instance
        return db_instance

    def describe_db_instances(self, db_instance_identifier=None, **kwargs):
        if db_instance_identifier:
            if db_instance_identifier in self.db_instances:
                return [self.db_instances[db_instance_identifier]]
            else:
                raise DBInstanceNotFound(db_instance_identifier)
        return self.db_instances.values()

    def modify_db_instance(self, db_instance_identifier, **db_kwargs):
        database = self.get_db_instance(db_instance_identifier)
        if "new_db_instance_identifier" in db_kwargs:
            del self.db_instances[db_instance_identifier]
            db_instance_identifier = db_kwargs[
                "db_instance_identifier"
            ] = db_kwargs.pop("new_db_instance_identifier")
            self.db_instances[db_instance_identifier] = database
        database.update(db_kwargs)
        return database

    def reboot_db_instance(self, db_instance_identifier=None, **kwargs):
        database = self.get_db_instance(db_instance_identifier)
        database.reboot()
        return database

    def stop_db_instance(self, db_instance_identifier, db_snapshot_identifier=None):
        database = self.get_db_instance(db_instance_identifier)
        # todo: certain rds types not allowed to be stopped at this time.
        if database.is_replica or database.multi_az:
            # todo: more db types not supported by stop/start instance api
            raise InvalidDBClusterStateFault(db_instance_identifier)
        if database.status != "available":
            raise InvalidDBInstanceState(db_instance_identifier, "stop")
        if db_snapshot_identifier:
            self.create_db_snapshot(db_instance_identifier, db_snapshot_identifier)
        database.status = "stopped"
        return database

    def start_db_instance(self, db_instance_identifier):
        database = self.get_db_instance(db_instance_identifier)
        # todo: bunch of different error messages to be generated from this api call
        if database.status != "stopped":
            raise InvalidDBInstanceState(db_instance_identifier, "start")
        database.status = "available"
        return database

    def find_db_from_id(self, db_id):
        if self.arn_regex.match(db_id):
            arn_breakdown = db_id.split(":")
            region = arn_breakdown[3]
            backend = self.get_regional_backend(region)
            db_name = arn_breakdown[-1]
        else:
            backend = self
            db_name = db_id

        return backend.get_db_instance(db_name)

    def delete_db_instance(
        self,
        db_instance_identifier,
        final_db_snapshot_identifier=None,
        skip_final_snapshot=False,
    ):
        db_instance = self.get_db_instance(db_instance_identifier)
        if final_db_snapshot_identifier and not skip_final_snapshot:
            self.create_db_snapshot(
                db_instance_identifier, final_db_snapshot_identifier
            )
        automated_snapshots = self.describe_db_snapshots(
            db_instance_identifier,
            db_snapshot_identifier=None,
            snapshot_type="automated",
        )
        for snapshot in automated_snapshots:
            self.delete_db_snapshot(snapshot.resource_id)
        db_instance.delete_events()
        db_instance.status = "deleting"
        return self.db_instances.pop(db_instance_identifier)

    def _validate_create_instance_args(self, kwargs):
        # TODO: Maybe move a lot of this to the __init__ method of the instance
        # https://stackoverflow.com/questions/1507082/python-is-it-bad-form-to-raise-exceptions-within-init
        # Check for boto default engine.  (Only doing this to avoid updating the
        # boto tests that don't explicitly specify an engine/version.)
        if kwargs.get("engine") in ["MySQL5.1", "MySQL"]:
            kwargs["engine"] = "mysql"
        engine = kwargs.get("engine")
        if engine not in utils.VALID_DB_INSTANCE_ENGINES:
            raise InvalidParameterValue("Invalid DB engine")
        if "engine_version" not in kwargs:
            kwargs["engine_version"] = utils.default_engine_version(engine)
        # FIXME: Can't uncomment the below until we can account for Major Versions being
        # passed in, e.g. postgres 9.6
        # if kwargs['engine_version'] not in utils.valid_engine_versions(engine):
        #     msg = 'Cannot find version {} for {}'.format(kwargs['engine_version'], engine)
        #     raise InvalidParameterValue(msg)
        # if 'db_parameter_group_name' not in kwargs:
        #     # TODO: Do we want to create a param group if the default doesn't exist?
        #     # param_group = self.get_db_parameter_group(utils.default_db_parameter_group_name(engine))
        #     # kwargs['db_parameter_group_name'] = param_group.name
        #     kwargs['db_parameter_group_name'] = utils.default_db_parameter_group_name(engine)
        if "option_group_name" not in kwargs:
            option_group_name = utils.default_option_group_name(
                engine, kwargs["engine_version"]
            )
            # TODO: Do we want to create an option group if the default doesn't exist?
            # option_group = self.get_option_group(option_group_name)
            kwargs["option_group_name"] = option_group_name
        if kwargs.get("availability_zone") and kwargs.get("multi_az"):
            msg = "Requesting a specific availability zone is not valid for Multi-AZ instances."
            raise InvalidParameterCombination(msg)
        availability_zones = [
            zone.name for zone in self.ec2.describe_availability_zones()
        ]
        if "availability_zone" not in kwargs:
            kwargs["availability_zone"] = random.choice(availability_zones)
        if kwargs["availability_zone"] not in availability_zones:
            raise InvalidAvailabilityZones(kwargs["availability_zone"])
        if "db_subnet_group_name" in kwargs:
            kwargs["db_subnet_group"] = self.get_db_subnet_group(
                kwargs["db_subnet_group_name"]
            )
        if "port" not in kwargs:
            kwargs["port"] = utils.default_engine_port(engine)
        # Certain parameters are not applicable for Aurora instances.
        if kwargs.get("db_cluster_identifier") is not None:
            msg = None
            if "allocated_storage" in kwargs:
                msg = (
                    "The requested DB instance will be a member of a DB cluster. "
                    "You don't need to set storage size."
                )
            if "master_username" in kwargs:
                msg = (
                    "The requested DB Instance will be a member of a DB Cluster. "
                    "Set master user name for the DB Cluster."
                )
            if "master_user_password" in kwargs:
                msg = (
                    "The requested DB Instance will be a member of a DB Cluster. "
                    "Set master user password for the DB Cluster."
                )
            if "db_name" in kwargs:
                msg = (
                    "The requested DB Instance will be a member of a DB Cluster. "
                    "Set database name for the DB Cluster."
                )
            # TODO: Check engine version, if passed, matches cluster.  Default to cluster
            # version (in DBInstance constructor) if not passed.
            # The engine version that you requested for your DB instance (xx) does not match
            # the engine version of your DB cluster (9.6.3).
            if msg:
                raise InvalidParameterCombination(msg)
        return kwargs
