from __future__ import unicode_literals

import boto.rds
from jinja2 import Template

from moto.core import BaseBackend
from .exceptions import DBInstanceNotFoundError, DBSecurityGroupNotFoundError


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

        self.security_groups = kwargs.get('security_groups', [])

        # PreferredBackupWindow
        # PreferredMaintenanceWindow
        # backup_retention_period = self._get_param("BackupRetentionPeriod")
        # OptionGroupName
        # DBParameterGroupName
        # VpcSecurityGroupIds.member.N

    @property
    def address(self):
        return "{}.aaaaaaaaaa.{}.rds.amazonaws.com".format(self.db_instance_identifier, self.region)

    def update(self, db_kwargs):
        for key, value in db_kwargs.items():
            if value is not None:
                setattr(self, key, value)

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
                {% for security_group in database.security_groups %}
                <DBSecurityGroup>
                  <Status>active</Status>
                  <DBSecurityGroupName>{{ security_group }}</DBSecurityGroupName>
                </DBSecurityGroup>
                {% endfor %}
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


class SecurityGroup(object):
    def __init__(self, group_name, description):
        self.group_name = group_name
        self.description = description
        self.ip_ranges = []

    def to_xml(self):
        template = Template("""<DBSecurityGroup>
            <EC2SecurityGroups/>
            <DBSecurityGroupDescription>{{ security_group.description }}</DBSecurityGroupDescription>
            <IPRanges>
            {% for ip_range in security_group.ip_ranges %}
                <IPRange>
                    <CIDRIP>{{ ip_range }}</CIDRIP>
                    <Status>authorized</Status>
                </IPRange>
            {% endfor %}
            </IPRanges>
            <OwnerId>{{ security_group.ownder_id }}</OwnerId>
            <DBSecurityGroupName>{{ security_group.group_name }}</DBSecurityGroupName>
        </DBSecurityGroup>""")
        return template.render(security_group=self)

    def authorize(self, cidr_ip):
        self.ip_ranges.append(cidr_ip)


class RDSBackend(BaseBackend):

    def __init__(self):
        self.databases = {}
        self.security_groups = {}

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

    def modify_database(self, db_instance_identifier, db_kwargs):
        database = self.describe_databases(db_instance_identifier)[0]
        database.update(db_kwargs)
        return database

    def delete_database(self, db_instance_identifier):
        if db_instance_identifier in self.databases:
            return self.databases.pop(db_instance_identifier)
        else:
            raise DBInstanceNotFoundError(db_instance_identifier)

    def create_security_group(self, group_name, description):
        security_group = SecurityGroup(group_name, description)
        self.security_groups[group_name] = security_group
        return security_group

    def describe_security_groups(self, security_group_name):
        if security_group_name:
            if security_group_name in self.security_groups:
                return [self.security_groups[security_group_name]]
            else:
                raise DBSecurityGroupNotFoundError(security_group_name)
        return self.security_groups.values()

    def delete_security_group(self, security_group_name):
        if security_group_name in self.security_groups:
            return self.security_groups.pop(security_group_name)
        else:
            raise DBSecurityGroupNotFoundError(security_group_name)

    def authorize_security_group(self, security_group_name, cidr_ip):
        security_group = self.describe_security_groups(security_group_name)[0]
        security_group.authorize(cidr_ip)
        return security_group

rds_backends = {}
for region in boto.rds.regions():
    rds_backends[region.name] = RDSBackend()
