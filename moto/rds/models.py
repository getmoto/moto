from __future__ import unicode_literals

import boto.rds
from jinja2 import Template

from moto.core import BaseBackend
from .exceptions import DBInstanceNotFoundError


class Database(object):
    def __init__(self, **kwargs):
        self.status = "available"

        self.region = kwargs.get('region')
        self.engine = kwargs.get("engine")
        self.engine_version = kwargs.get("engine_version")
        self.iops = kwargs.get("iops")
        self.storage_type = kwargs.get("storage_type")
        self.master_username = kwargs.get('master_username')
        self.master_password = kwargs.get('master_password')
        self.auto_minor_version_upgrade = kwargs.get('auto_minor_version_upgrade')
        self.allocated_storage = kwargs.get('allocated_storage')
        self.db_instance_identifier = kwargs.get('db_instance_identifier')
        self.db_instance_class = kwargs.get('db_instance_class')
        self.port = kwargs.get('port')
        self.db_instance_identifier = kwargs.get('db_instance_identifier')
        self.db_name = kwargs.get("db_name")
        self.publicly_accessible = kwargs.get("publicly_accessible")

        self.backup_retention_period = kwargs.get("backup_retention_period")
        if self.backup_retention_period is None:
            self.backup_retention_period = 1

        self.availability_zone = kwargs.get("availability_zone")
        self.multi_az = kwargs.get("multi_az")
        self.db_subnet_group_name = kwargs.get("db_subnet_group_name")

        # PreferredBackupWindow
        # PreferredMaintenanceWindow
        # backup_retention_period = self._get_param("BackupRetentionPeriod")
        # OptionGroupName
        # DBParameterGroupName
        # DBSecurityGroups.member.N
        # VpcSecurityGroupIds.member.N

    @property
    def address(self):
        return "{}.aaaaaaaaaa.{}.rds.amazonaws.com".format(self.db_instance_identifier, self.region)

    def to_xml(self):
        template = Template("""<DBInstance>
              <BackupRetentionPeriod>{{ database.backup_retention_period }}</BackupRetentionPeriod>
              <DBInstanceStatus>{{ database.status }}</DBInstanceStatus>
              <MultiAZ>{{ database.multi_az }}</MultiAZ>
              <VpcSecurityGroups/>
              <DBInstanceIdentifier>{{ database.db_instance_identifier }}</DBInstanceIdentifier>
              <PreferredBackupWindow>03:50-04:20</PreferredBackupWindow>
              <PreferredMaintenanceWindow>wed:06:38-wed:07:08</PreferredMaintenanceWindow>
              <ReadReplicaDBInstanceIdentifiers/>
              <Engine>{{ database.engine }}</Engine>
              <LicenseModel>general-public-license</LicenseModel>
              <EngineVersion>{{ database.engine_version }}</EngineVersion>
              <DBParameterGroups>
              </DBParameterGroups>
              <OptionGroupMemberships>
              </OptionGroupMemberships>
              <DBSecurityGroups>
                <DBSecurityGroup>
                  <Status>active</Status>
                  <DBSecurityGroupName>default</DBSecurityGroupName>
                </DBSecurityGroup>
              </DBSecurityGroups>
              <PubliclyAccessible>{{ database.publicly_accessible }}</PubliclyAccessible>
              <AutoMinorVersionUpgrade>{{ database.auto_minor_version_upgrade }}</AutoMinorVersionUpgrade>
              <AllocatedStorage>{{ database.allocated_storage }}</AllocatedStorage>
              <DBInstanceClass>{{ database.db_instance_class }}</DBInstanceClass>
              <MasterUsername>{{ database.master_username }}</MasterUsername>
              <Endpoint>
                <Address>{{ database.address }}</Address>
                <Port>{{ database.port }}</Port>
              </Endpoint>
            </DBInstance>""")
        return template.render(database=self)


class RDSBackend(BaseBackend):

    def __init__(self):
        self.databases = {}

    def create_database(self, db_kwargs):
        database_id = db_kwargs['db_instance_identifier']
        database = Database(**db_kwargs)
        self.databases[database_id] = database
        return database

    def describe_databases(self, db_instance_identifier=None):
        if db_instance_identifier:
            if db_instance_identifier in self.databases:
                return [self.databases[db_instance_identifier]]
            else:
                raise DBInstanceNotFoundError(db_instance_identifier)
        return self.databases.values()

    def delete_database(self, db_instance_identifier):
        if db_instance_identifier in self.databases:
            return self.databases.pop(db_instance_identifier)
        else:
            raise DBInstanceNotFoundError(db_instance_identifier)


rds_backends = {}
for region in boto.rds.regions():
    rds_backends[region.name] = RDSBackend()
