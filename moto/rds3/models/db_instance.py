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
    InvalidParameterCombination)
from .base import BaseRDSBackend, BaseRDSModel
from .event import EventMixin
from .log import LogFileManager
from .tag import TaggableRDSResource
from .. import utils


class DBInstance(TaggableRDSResource, EventMixin, BaseRDSModel):

    event_source_type = 'db-instance'
    resource_type = 'db'

    def __init__(self, backend, identifier,
                 availability_zone,
                 db_instance_class,
                 engine,
                 engine_version,
                 option_group_name,
                 port,
                 allocated_storage=10,
                 backup_retention_period=1,
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
                 multi_az=False,
                 license_model='general-public-license',
                 preferred_backup_window='13:14-13:44',
                 preferred_maintenance_window='wed:06:38-wed:07:08',
                 promotion_tier=1,
                 publicly_accessible=None,
                 source_db_instance_identifier=None,
                 storage_type='standard',
                 storage_encrypted=False,
                 tags=None,
                 vpc_security_group_ids=None,
                 **kwargs):
        super(DBInstance, self).__init__(backend)
        # TODO: If cluster identifier is passed in a lot of the settings have to come
        # from the cluster...not the kwargs
        self.db_instance_identifier = identifier
        self.status = "available"

        self.engine = engine
        self.engine_version = engine_version

        self.port = port
        self.db_name = db_name

        self.iops = iops
        self.storage_type = 'io1' if self.iops else storage_type

        self.storage_encrypted = storage_encrypted
        if self.storage_encrypted:
            self.kms_key_id = kwargs.get("kms_key_id", "default_kms_key_id")
        else:
            self.kms_key_id = kwargs.get("kms_key_id")

        self.master_username = master_username
        self.master_user_password = master_user_password
        self.auto_minor_version_upgrade = auto_minor_version_upgrade
        self.allocated_storage = allocated_storage
        self.db_cluster_identifier = db_cluster_identifier
        self.is_cluster_writer = False
        if 'character_set_name' in kwargs and kwargs['character_set_name']:
            self.character_set_name = kwargs.get('character_set_name')
        # TODO: I think we need to move this up and rethink some
        # of this stuff that's not applicable for Aurora.
        if self.db_cluster_identifier:
            cluster = self.backend.get_db_cluster(self.db_cluster_identifier)
            if not cluster.members:
                self.is_cluster_writer = True
            self.db_name = cluster.database_name
            self.storage_encrypted = cluster.storage_encrypted
            self.engine_version = cluster.engine_version
            if hasattr(cluster, 'character_set_name'):
                self.character_set_name = cluster.character_set_name

        self.promotion_tier = promotion_tier
        self.read_replica_source_db_instance_identifier = source_db_instance_identifier
        self.db_instance_class = db_instance_class

        self.publicly_accessible = publicly_accessible
        if self.publicly_accessible is None:
            self.publicly_accessible = False if db_subnet_group else True

        self.backup_retention_period = backup_retention_period
        self.availability_zone = availability_zone

        self.multi_az = multi_az

        self.db_subnet_group = db_subnet_group

        self._db_security_groups = db_security_groups or []
        self.vpc_security_group_ids = vpc_security_group_ids or []
        self.preferred_maintenance_window = preferred_maintenance_window

        if db_parameter_group_name is None:
            self.db_parameter_group_name = utils.default_db_parameter_group_name(self.engine, self.engine_version)
        else:
            self.db_parameter_group_name = db_parameter_group_name

        self._db_parameter_groups = [{'name': self.db_parameter_group_name, 'status': 'in-sync'}]
        self.preferred_backup_window = preferred_backup_window
        self.license_model = license_model

        self.option_group_name = option_group_name
        self._option_groups = [{'name': self.option_group_name, 'status': 'in-sync'}]

        self.copy_tags_to_snapshot = copy_tags_to_snapshot
        if tags:
            self.add_tags(tags)

        self.log_file_manager = LogFileManager(self.engine)

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
            {
                'status': 'active',
                'db_security_group_name': security_group
            } for security_group in self._db_security_groups
        ]

    @db_security_groups.setter
    def db_security_groups(self, value):
        self._db_security_groups = value

    @property
    def db_parameter_groups(self):
        return [
            {
                'parameter_apply_status': db_parameter_group['status'],
                'db_parameter_group_name': db_parameter_group['name']
            } for db_parameter_group in self._db_parameter_groups
        ]

    @property
    def option_group_memberships(self):
        return [
            {
                'status': option_group['status'],
                'option_group_name': option_group['name']
            } for option_group in self._option_groups
        ]

    @property
    def endpoint(self):
        return {
            'address': self.address,
            'port': self.port
        }

    @property
    def read_replica_db_instance_identifiers(self):
        return [replica for replica in self.read_replicas]

    @property
    def status_infos(self):
        if self.is_replica:
            return [
                {
                    'status_type': 'read replication',
                    'status': 'replicating',
                    'normal': True,
                    'message': None
                }
            ]
        else:
            return None

    @property
    def vpc_security_groups(self):
        return [
            {
                'status': 'active',
                'vpc_security_group_id': group_id
            } for group_id in self.vpc_security_group_ids
        ]

    # @property
    # def db_subnet_group(self):
    #     return {
    #         'db_subnet_group_name': self.db_subnet_group.subnet_name,
    #         'db_subnet_group_description': self.db_subnet_group.description,
    #         'SubnetGroupStatus': self.db_subnet_group.status,
    #         'Subnets': {
    #             'Subnet': [
    #                 {
    #                     'SubnetStatus': 'Active',
    #                     'SubnetIdentifier': subnet.id,
    #                     'SubnetAvailabilityZone': {
    #                         'Name': subnet.availability_zone,
    #                         'ProvisionedIopsCapable': False
    #                     }
    #                 } for subnet in self.db_subnet_group.subnets
    #                 ]
    #         },
    #         'VpcId': self.db_subnet_group.vpc_id
    #     }

    def to_dict(self):
        data = {
            'BackupRetentionPeriod': self.backup_retention_period,
            'DBInstanceStatus': self.status,
            'DBName': self.db_name,  # TODO: Maybe this is optional?
            'MultiAZ': self.multi_az,
            'VpcSecurityGroups': {
                'VpcSecurityGroup': [
                    {

                        'Status': 'active',
                        'VpcSecurityGroupId': group_id
                    } for group_id in self.vpc_security_group_ids
                ]
            },
            'DBInstanceIdentifier': self.resource_id,
            'PreferredBackupWindow': '03:50-04:20',
            'PreferredMaintenanceWindow': 'wed:06:38-wed:07:08',
            'ReadReplicaDBInstanceIdentifiers': {
                'ReadReplicaDBInstanceIdentifier': [replica for replica in self.read_replicas]
            },
            'Engine': self.engine,
            'LicenseModel': self.license_model,
            'EngineVersion': self.engine_version,
            # TODO: Return OptionGroupMemberships
            'OptionGroupMemberships': {'OptionGroupMembership': []},
            'DBParameterGroups': {
                'DBParameterGroup': [
                    {
                        'ParameterApplyStatus': db_parameter_group['status'],
                        'DBParameterGroupName': db_parameter_group['name']
                    } for db_parameter_group in self.db_parameter_groups
                ]
            },
            'DBSecurityGroups': {
                'DBSecurityGroup': [
                    {
                        'Status': 'active',
                        'DBSecurityGroupName': security_group
                    } for security_group in self.security_groups
                ]
            },
            'PubliclyAccessible': self.publicly_accessible,
            'AutoMinorVersionUpgrade': self.auto_minor_version_upgrade,
            'AllocatedStorage': self.allocated_storage,
            'StorageEncrypted': self.storage_encrypted,

            'KmsKeyId': self.kms_key_id,

            'DBInstanceClass': self.db_instance_class,
            'MasterUsername': self.master_username,
            'Endpoint': {
                'Address': self.address,
                'Port': self.port
            },
            'DBInstanceArn': self.arn,
            'CopyTagsToSnapshot': self.copy_tags_to_snapshot,
            'StorageType': self.storage_type,
            'PendingModifiedValues': {}
        }
        if self.db_cluster_identifier:
            data['PromotionTier'] = self.promotion_tier
        if self.iops:
            data['Iops'] = self.iops
        if self.db_subnet_group:
            data['DBSubnetGroup'] = {
                'DBSubnetGroupName': self.db_subnet_group.subnet_name,
                'DBSubnetGroupDescription': self.db_subnet_group.description,
                'SubnetGroupStatus': self.db_subnet_group.status,
                'Subnets': {
                    'Subnet': [
                        {
                            'SubnetStatus': 'Active',
                            'SubnetIdentifier': subnet.id,
                            'SubnetAvailabilityZone': {
                                'Name': subnet.availability_zone,
                                'ProvisionedIopsCapable': False
                            }
                        } for subnet in self.db_subnet_group.subnets
                    ]
                },
                'VpcId': self.db_subnet_group.vpc_id}
        if self.is_replica:
            data['ReadReplicaSourceDBInstanceIdentifier'] = self.source_db_identifier
            data['StatusInfos'] = {
                'DBInstanceStatusInfo': [
                    {
                        'StatusType': 'read replication',
                        'Status': 'replicating',
                        'Normal': True,
                        'Message': None
                    }
                ]
            }
        if self.db_cluster_identifier:
            data['DBClusterIdentifier'] = self.db_cluster_identifier
        return data

    @property
    def address(self):
        return "{0}.aaaaaaaaaa.{1}.rds.amazonaws.com".format(self.resource_id, self.backend.region)

    def update(self, db_kwargs):
        # TODO: This is all horrible.  Must fix.
        if db_kwargs.get('db_parameter_group_name'):
            db_parameter_group_name = db_kwargs.pop('db_parameter_group_name')
            self._db_parameter_groups = [{'name': db_parameter_group_name, 'status': 'pending-reboot'}]
        # TODO: This is all horrible.  Must fix.
        if db_kwargs.get('option_group_name'):
            option_group_name = db_kwargs.pop('option_group_name')
            self._option_groups = [{'name': option_group_name, 'status': 'in-sync'}]
        # Hack: get instance id before tags, because tags depend on resource_id for arn...
        if 'db_instance_identifier' in db_kwargs:
            self.db_instance_identifier = db_kwargs.pop('db_instance_identifier')
        self.add_tags(db_kwargs.pop('tags', []))
        for key, value in db_kwargs.items():
            if value:
                setattr(self, key, value)

    def reboot(self):
        for param_group in self._db_parameter_groups:
            if param_group['status'] == 'pending-reboot':
                param_group['status'] = 'in-sync'

    def get_cfn_attribute(self, attribute_name):
        if attribute_name == 'Endpoint.Address':
            return self.address
        elif attribute_name == 'Endpoint.Port':
            return self.port
        raise UnformattedGetAttTemplateException()

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']
        if 'DBInstanceIdentifier' not in properties:
            properties['DBInstanceIdentifier'] = resource_name.lower() + get_random_hex(12)
        backend = cls.get_regional_backend(region_name)
        if 'SourceDBInstanceIdentifier' in properties:
            params = utils.parse_cf_properties('CreateDBInstanceReadReplica', properties)
            db_instance = backend.create_db_instance_read_replica(**params)
        else:
            params = utils.parse_cf_properties('CreateDBInstance', properties)
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
                    if db_instance.read_replica_source_db_instance_identifier == self.resource_id:
                        replicas.append(db_instance.resource_id)
                else:
                    if db_instance.read_replica_source_db_instance_identifier == self.arn:
                        replicas.append(db_instance.arn)
        return replicas


class DBInstanceBackend(BaseRDSBackend):

    def __init__(self):
        super(DBInstanceBackend, self).__init__()
        self.db_instances = OrderedDict()
        self.arn_regex = re_compile(
            r'^arn:aws:rds:.*:[0-9]*:(db|es|og|pg|ri|secgrp|snapshot|subgrp):.*$')

    def get_db_instance(self, db_instance_identifier):
        if db_instance_identifier not in self.db_instances:
            raise DBInstanceNotFound(db_instance_identifier)
        return self.db_instances[db_instance_identifier]

    def _backup_db_instance(self, db_instance):
        # TODO: Make this method on DBInstance?
        db_instance.add_event('DB_INSTANCE_BACKUP_START')
        time_stamp = datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M')
        snapshot_id = 'rds:{}-{}'.format(db_instance.resource_id, time_stamp)
        self.create_db_snapshot(db_instance.resource_id, snapshot_id, snapshot_type='automated')
        db_instance.add_event('DB_INSTANCE_BACKUP_FINISH')

    def create_db_instance(self, db_instance_identifier, **kwargs):
        if db_instance_identifier in self.db_instances:
            raise DBInstanceAlreadyExists()
        instance_kwargs = self._validate_create_instance_args(kwargs)
        db_instance = DBInstance(self, db_instance_identifier, **instance_kwargs)
        self.db_instances[db_instance_identifier] = db_instance
        db_instance.add_event('DB_INSTANCE_CREATE')
        # snapshot_id = '{}-{}'.format(db_instance_identifier, datetime.datetime.utcnow().strftime('%Y-%m-%d-%H-%M'))
        # self.create_db_snapshot(db_instance_identifier, snapshot_id, snapshot_type='automated')
        self._backup_db_instance(db_instance)
        return db_instance

    def restore_db_instance_from_db_snapshot(self, db_instance_identifier, db_snapshot_identifier, **kwargs):
        snapshot = self.get_db_snapshot(db_snapshot_identifier)
        db_args = dict(**snapshot.db_instance.__dict__)
        # AWS restores the database with most of the original configuration,
        # but with the default security/parameter group.
        params_to_remove = ['vpc_security_group_ids', 'db_security_groups', 'db_parameter_group_name']
        for param in params_to_remove:
            db_args.pop(param, None)
        # Use our backend and update with any user-provided parameters.
        db_args.update(backend=self, **kwargs)
        db_args = self._validate_create_instance_args(db_args)
        db_instance = DBInstance(identifier=db_instance_identifier, **db_args)
        self.db_instances[db_instance_identifier] = db_instance
        return db_instance

    def create_db_instance_read_replica(self, db_instance_identifier, source_db_instance_identifier,
                                        multi_az=False, **kwargs):
        source_db_instance = self.find_db_from_id(source_db_instance_identifier)
        db_args = dict(**source_db_instance.__dict__)
        if source_db_instance.region != self.region or multi_az:
            db_args.pop('availability_zone', None)
        # Use our backend and update with any user-provided parameters.
        db_args.update(backend=self, multi_az=multi_az, **kwargs)
        db_args = self._validate_create_instance_args(db_args)
        db_instance = DBInstance(identifier=db_instance_identifier,
                                 source_db_instance_identifier=source_db_instance_identifier,
                                 **db_args)
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
        if 'new_db_instance_identifier' in db_kwargs:
            del self.db_instances[db_instance_identifier]
            db_instance_identifier = db_kwargs['db_instance_identifier'] = db_kwargs.pop('new_db_instance_identifier')
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
        if database.status != 'available':
            raise InvalidDBInstanceState(db_instance_identifier, 'stop')
        if db_snapshot_identifier:
            self.create_db_snapshot(db_instance_identifier, db_snapshot_identifier)
        database.status = 'stopped'
        return database

    def start_db_instance(self, db_instance_identifier):
        database = self.get_db_instance(db_instance_identifier)
        # todo: bunch of different error messages to be generated from this api call
        if database.status != 'stopped':
            raise InvalidDBInstanceState(db_instance_identifier, 'start')
        database.status = 'available'
        return database

    def find_db_from_id(self, db_id):
        if self.arn_regex.match(db_id):
            arn_breakdown = db_id.split(':')
            region = arn_breakdown[3]
            backend = self.get_regional_backend(region)
            db_name = arn_breakdown[-1]
        else:
            backend = self
            db_name = db_id

        return backend.get_db_instance(db_name)

    def delete_db_instance(self, db_instance_identifier, final_db_snapshot_identifier=None, skip_final_snapshot=False):
        db_instance = self.get_db_instance(db_instance_identifier)
        if final_db_snapshot_identifier and not skip_final_snapshot:
            self.create_db_snapshot(db_instance_identifier, final_db_snapshot_identifier)
        automated_snapshots = self.describe_db_snapshots(db_instance_identifier, db_snapshot_identifier=None,
                                                         snapshot_type='automated')
        for snapshot in automated_snapshots:
            self.delete_db_snapshot(snapshot.resource_id)
        db_instance.delete_events()
        db_instance.status = 'deleting'
        return self.db_instances.pop(db_instance_identifier)

    def _validate_create_instance_args(self, kwargs):
        # TODO: Maybe move a lot of this to the __init__ method of the instance
        # https://stackoverflow.com/questions/1507082/python-is-it-bad-form-to-raise-exceptions-within-init
        # Check for boto default engine.  (Only doing this to avoid updating the
        # boto tests that don't explicitly specify an engine/version.)
        if kwargs.get('engine') in ['MySQL5.1', 'MySQL']:
            kwargs['engine'] = 'mysql'
        engine = kwargs.get('engine')
        if engine not in utils.VALID_DB_INSTANCE_ENGINES:
            raise InvalidParameterValue('Invalid DB engine')
        if 'engine_version' not in kwargs:
            kwargs['engine_version'] = utils.default_engine_version(engine)
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
        if 'option_group_name' not in kwargs:
            option_group_name = utils.default_option_group_name(engine, kwargs['engine_version'])
            # TODO: Do we want to create an option group if the default doesn't exist?
            # option_group = self.get_option_group(option_group_name)
            kwargs['option_group_name'] = option_group_name
        if kwargs.get('availability_zone') and kwargs.get('multi_az'):
            msg = 'Requesting a specific availability zone is not valid for Multi-AZ instances.'
            raise InvalidParameterCombination(msg)
        availability_zones = [zone.name for zone in self.ec2.describe_availability_zones()]
        if 'availability_zone' not in kwargs:
            kwargs['availability_zone'] = random.choice(availability_zones)
        if kwargs['availability_zone'] not in availability_zones:
            raise InvalidAvailabilityZones(kwargs['availability_zone'])
        if 'db_subnet_group_name' in kwargs:
            kwargs['db_subnet_group'] = self.get_db_subnet_group(kwargs['db_subnet_group_name'])
        if 'port' not in kwargs:
            kwargs['port'] = utils.default_engine_port(engine)
        # Certain parameters are not applicable for Aurora instances.
        if kwargs.get('db_cluster_identifier') is not None:
            msg = None
            if 'allocated_storage' in kwargs:
                msg = 'The requested DB instance will be a member of a DB cluster. ' \
                      'You don\'t need to set storage size.'
            if 'master_username' in kwargs:
                msg = 'The requested DB Instance will be a member of a DB Cluster. ' \
                      'Set master user name for the DB Cluster.'
            if 'master_user_password' in kwargs:
                msg = 'The requested DB Instance will be a member of a DB Cluster. ' \
                      'Set master user password for the DB Cluster.'
            if 'db_name' in kwargs:
                msg = 'The requested DB Instance will be a member of a DB Cluster. ' \
                      'Set database name for the DB Cluster.'
            # TODO: Check engine version, if passed, matches cluster.  Default to cluster
            # version (in DBInstance constructor) if not passed.
            # The engine version that you requested for your DB instance (xx) does not match
            # the engine version of your DB cluster (9.6.3).
            if msg:
                raise InvalidParameterCombination(msg)
        return kwargs