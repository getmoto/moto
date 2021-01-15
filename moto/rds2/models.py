from __future__ import unicode_literals

import copy
import datetime
import os

from collections import defaultdict
from boto3 import Session
from jinja2 import Template
from re import compile as re_compile
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel, CloudFormationModel, ACCOUNT_ID

from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.ec2.models import ec2_backends
from .exceptions import (
    RDSClientError,
    DBInstanceNotFoundError,
    DBSnapshotNotFoundError,
    DBSecurityGroupNotFoundError,
    DBSubnetGroupNotFoundError,
    DBParameterGroupNotFoundError,
    OptionGroupNotFoundFaultError,
    InvalidDBClusterStateFaultError,
    InvalidDBInstanceStateError,
    SnapshotQuotaExceededError,
    DBSnapshotAlreadyExistsError,
    InvalidParameterValue,
    InvalidParameterCombination,
)
from .utils import FilterDef, apply_filter, merge_filters, validate_filters


class Database(CloudFormationModel):

    SUPPORTED_FILTERS = {
        "db-cluster-id": FilterDef(None, "DB Cluster Identifiers"),
        "db-instance-id": FilterDef(
            ["db_instance_arn", "db_instance_identifier"], "DB Instance Identifiers"
        ),
        "dbi-resource-id": FilterDef(["dbi_resource_id"], "Dbi Resource Ids"),
        "domain": FilterDef(None, ""),
        "engine": FilterDef(["engine"], "Engine Names"),
    }

    default_engine_versions = {
        "MySQL": "5.6.21",
        "mysql": "5.6.21",
        "oracle-se1": "11.2.0.4.v3",
        "oracle-se": "11.2.0.4.v3",
        "oracle-ee": "11.2.0.4.v3",
        "sqlserver-ee": "11.00.2100.60.v1",
        "sqlserver-se": "11.00.2100.60.v1",
        "sqlserver-ex": "11.00.2100.60.v1",
        "sqlserver-web": "11.00.2100.60.v1",
        "postgres": "9.3.3",
    }

    def __init__(self, **kwargs):
        self.status = "available"
        self.is_replica = False
        self.replicas = []
        self.region = kwargs.get("region")
        self.engine = kwargs.get("engine")
        self.engine_version = kwargs.get("engine_version", None)
        if not self.engine_version and self.engine in self.default_engine_versions:
            self.engine_version = self.default_engine_versions[self.engine]
        self.iops = kwargs.get("iops")
        self.storage_encrypted = kwargs.get("storage_encrypted", False)
        if self.storage_encrypted:
            self.kms_key_id = kwargs.get("kms_key_id", "default_kms_key_id")
        else:
            self.kms_key_id = kwargs.get("kms_key_id")
        self.storage_type = kwargs.get("storage_type")
        if self.storage_type is None:
            self.storage_type = Database.default_storage_type(iops=self.iops)
        self.master_username = kwargs.get("master_username")
        self.master_user_password = kwargs.get("master_user_password")
        self.auto_minor_version_upgrade = kwargs.get("auto_minor_version_upgrade")
        if self.auto_minor_version_upgrade is None:
            self.auto_minor_version_upgrade = True
        self.allocated_storage = kwargs.get("allocated_storage")
        if self.allocated_storage is None:
            self.allocated_storage = Database.default_allocated_storage(
                engine=self.engine, storage_type=self.storage_type
            )
        self.db_instance_identifier = kwargs.get("db_instance_identifier")
        self.source_db_identifier = kwargs.get("source_db_identifier")
        self.db_instance_class = kwargs.get("db_instance_class")
        self.port = kwargs.get("port")
        if self.port is None:
            self.port = Database.default_port(self.engine)
        self.db_instance_identifier = kwargs.get("db_instance_identifier")
        self.db_name = kwargs.get("db_name")
        self.instance_create_time = iso_8601_datetime_with_milliseconds(
            datetime.datetime.now()
        )
        self.publicly_accessible = kwargs.get("publicly_accessible")
        if self.publicly_accessible is None:
            self.publicly_accessible = True
        self.copy_tags_to_snapshot = kwargs.get("copy_tags_to_snapshot")
        if self.copy_tags_to_snapshot is None:
            self.copy_tags_to_snapshot = False
        self.backup_retention_period = kwargs.get("backup_retention_period")
        if self.backup_retention_period is None:
            self.backup_retention_period = 1
        self.availability_zone = kwargs.get("availability_zone")
        self.multi_az = kwargs.get("multi_az")
        self.db_subnet_group_name = kwargs.get("db_subnet_group_name")
        if self.db_subnet_group_name:
            self.db_subnet_group = rds2_backends[self.region].describe_subnet_groups(
                self.db_subnet_group_name
            )[0]
        else:
            self.db_subnet_group = None
        self.security_groups = kwargs.get("security_groups", [])
        self.vpc_security_group_ids = kwargs.get("vpc_security_group_ids", [])
        self.preferred_maintenance_window = kwargs.get(
            "preferred_maintenance_window", "wed:06:38-wed:07:08"
        )
        self.db_parameter_group_name = kwargs.get("db_parameter_group_name")
        if (
            self.db_parameter_group_name
            and not self.is_default_parameter_group(self.db_parameter_group_name)
            and self.db_parameter_group_name
            not in rds2_backends[self.region].db_parameter_groups
        ):
            raise DBParameterGroupNotFoundError(self.db_parameter_group_name)

        self.preferred_backup_window = kwargs.get(
            "preferred_backup_window", "13:14-13:44"
        )
        self.license_model = kwargs.get("license_model", "general-public-license")
        self.option_group_name = kwargs.get("option_group_name", None)
        if (
            self.option_group_name
            and self.option_group_name not in rds2_backends[self.region].option_groups
        ):
            raise OptionGroupNotFoundFaultError(self.option_group_name)
        self.default_option_groups = {
            "MySQL": "default.mysql5.6",
            "mysql": "default.mysql5.6",
            "postgres": "default.postgres9.3",
        }
        if not self.option_group_name and self.engine in self.default_option_groups:
            self.option_group_name = self.default_option_groups[self.engine]
        self.character_set_name = kwargs.get("character_set_name", None)
        self.enable_iam_database_authentication = kwargs.get(
            "enable_iam_database_authentication", False
        )
        self.dbi_resource_id = "db-M5ENSHXFPU6XHZ4G4ZEI5QIO2U"
        self.tags = kwargs.get("tags", [])

    @property
    def db_instance_arn(self):
        return "arn:aws:rds:{0}:1234567890:db:{1}".format(
            self.region, self.db_instance_identifier
        )

    @property
    def physical_resource_id(self):
        return self.db_instance_identifier

    def db_parameter_groups(self):
        if not self.db_parameter_group_name or self.is_default_parameter_group(self.db_parameter_group_name):
            (
                db_family,
                db_parameter_group_name,
            ) = self.default_db_parameter_group_details()
            description = "Default parameter group for {0}".format(db_family)
            return [
                DBParameterGroup(
                    name=db_parameter_group_name,
                    family=db_family,
                    description=description,
                    tags={},
                    region=self.region,
                )
            ]
        else:
            return [
                rds2_backends[self.region].db_parameter_groups[
                    self.db_parameter_group_name
                ]
            ]

    def is_default_parameter_group(self, param_group_name):
        return param_group_name.startswith('default.%s' % self.engine.lower())

    def default_db_parameter_group_details(self):
        if not self.engine_version:
            return (None, None)

        minor_engine_version = ".".join(self.engine_version.rsplit(".")[:-1])
        db_family = "{0}{1}".format(self.engine.lower(), minor_engine_version)

        return db_family, "default.{0}".format(db_family)

    def to_xml(self):
        template = Template(
            """<DBInstance>
              <BackupRetentionPeriod>{{ database.backup_retention_period }}</BackupRetentionPeriod>
              <DBInstanceStatus>{{ database.status }}</DBInstanceStatus>
              {% if database.db_name %}<DBName>{{ database.db_name }}</DBName>{% endif %}
              <MultiAZ>{{ database.multi_az }}</MultiAZ>
              <VpcSecurityGroups>
                {% for vpc_security_group_id in database.vpc_security_group_ids %}
                <VpcSecurityGroupMembership>
                  <Status>active</Status>
                  <VpcSecurityGroupId>{{ vpc_security_group_id }}</VpcSecurityGroupId>
                </VpcSecurityGroupMembership>
                {% endfor %}
              </VpcSecurityGroups>
              <DBInstanceIdentifier>{{ database.db_instance_identifier }}</DBInstanceIdentifier>
              <DbiResourceId>{{ database.dbi_resource_id }}</DbiResourceId>
              <InstanceCreateTime>{{ database.instance_create_time }}</InstanceCreateTime>
              <PreferredBackupWindow>03:50-04:20</PreferredBackupWindow>
              <PreferredMaintenanceWindow>wed:06:38-wed:07:08</PreferredMaintenanceWindow>
              <ReadReplicaDBInstanceIdentifiers>
                {% for replica_id in database.replicas %}
                    <ReadReplicaDBInstanceIdentifier>{{ replica_id }}</ReadReplicaDBInstanceIdentifier>
                {% endfor %}
              </ReadReplicaDBInstanceIdentifiers>
              <StatusInfos>
                {% if database.is_replica %}
                <DBInstanceStatusInfo>
                    <StatusType>read replication</StatusType>
                    <Status>replicating</Status>
                    <Normal>true</Normal>
                    <Message></Message>
                </DBInstanceStatusInfo>
                {% endif %}
              </StatusInfos>
              {% if database.is_replica %}
              <ReadReplicaSourceDBInstanceIdentifier>{{ database.source_db_identifier }}</ReadReplicaSourceDBInstanceIdentifier>
              {% endif %}
              <Engine>{{ database.engine }}</Engine>
              <IAMDatabaseAuthenticationEnabled>{{database.enable_iam_database_authentication|lower }}</IAMDatabaseAuthenticationEnabled>
              <LicenseModel>{{ database.license_model }}</LicenseModel>
              <EngineVersion>{{ database.engine_version }}</EngineVersion>
              <OptionGroupMemberships>
                <OptionGroupMembership>
                  <OptionGroupName>{{ database.option_group_name }}</OptionGroupName>
                  <Status>in-sync</Status>
                </OptionGroupMembership>
              </OptionGroupMemberships>
              <DBParameterGroups>
                {% for db_parameter_group in database.db_parameter_groups() %}
                <DBParameterGroup>
                  <ParameterApplyStatus>in-sync</ParameterApplyStatus>
                  <DBParameterGroupName>{{ db_parameter_group.name }}</DBParameterGroupName>
                </DBParameterGroup>
                {% endfor %}
              </DBParameterGroups>
              <DBSecurityGroups>
                {% for security_group in database.security_groups %}
                <DBSecurityGroup>
                  <Status>active</Status>
                  <DBSecurityGroupName>{{ security_group }}</DBSecurityGroupName>
                </DBSecurityGroup>
                {% endfor %}
              </DBSecurityGroups>
              {% if database.db_subnet_group %}
              <DBSubnetGroup>
                <DBSubnetGroupName>{{ database.db_subnet_group.subnet_name }}</DBSubnetGroupName>
                <DBSubnetGroupDescription>{{ database.db_subnet_group.description }}</DBSubnetGroupDescription>
                <SubnetGroupStatus>{{ database.db_subnet_group.status }}</SubnetGroupStatus>
                <Subnets>
                    {% for subnet in database.db_subnet_group.subnets %}
                    <Subnet>
                      <SubnetStatus>Active</SubnetStatus>
                      <SubnetIdentifier>{{ subnet.id }}</SubnetIdentifier>
                      <SubnetAvailabilityZone>
                        <Name>{{ subnet.availability_zone }}</Name>
                        <ProvisionedIopsCapable>false</ProvisionedIopsCapable>
                      </SubnetAvailabilityZone>
                    </Subnet>
                    {% endfor %}
                </Subnets>
                <VpcId>{{ database.db_subnet_group.vpc_id }}</VpcId>
              </DBSubnetGroup>
              {% endif %}
              <PubliclyAccessible>{{ database.publicly_accessible }}</PubliclyAccessible>
              <CopyTagsToSnapshot>{{ database.copy_tags_to_snapshot }}</CopyTagsToSnapshot>
              <AutoMinorVersionUpgrade>{{ database.auto_minor_version_upgrade }}</AutoMinorVersionUpgrade>
              <AllocatedStorage>{{ database.allocated_storage }}</AllocatedStorage>
              <StorageEncrypted>{{ database.storage_encrypted }}</StorageEncrypted>
              {% if database.kms_key_id %}
              <KmsKeyId>{{ database.kms_key_id }}</KmsKeyId>
              {% endif %}
              {% if database.iops %}
              <Iops>{{ database.iops }}</Iops>
              <StorageType>io1</StorageType>
              {% else %}
              <StorageType>{{ database.storage_type }}</StorageType>
              {% endif %}
              <DBInstanceClass>{{ database.db_instance_class }}</DBInstanceClass>
              <MasterUsername>{{ database.master_username }}</MasterUsername>
              <Endpoint>
                <Address>{{ database.address }}</Address>
                <Port>{{ database.port }}</Port>
              </Endpoint>
              <DBInstanceArn>{{ database.db_instance_arn }}</DBInstanceArn>
              <TagList>
              {%- for tag in database.tags -%}
                <Tag>
                  <Key>{{ tag['Key'] }}</Key>
                  <Value>{{ tag['Value'] }}</Value>
                </Tag>
              {%- endfor -%}
              </TagList>
            </DBInstance>"""
        )
        return template.render(database=self)

    @property
    def address(self):
        return "{0}.aaaaaaaaaa.{1}.rds.amazonaws.com".format(
            self.db_instance_identifier, self.region
        )

    def add_replica(self, replica):
        self.replicas.append(replica.db_instance_identifier)

    def remove_replica(self, replica):
        self.replicas.remove(replica.db_instance_identifier)

    def set_as_replica(self):
        self.is_replica = True
        self.replicas = []

    def update(self, db_kwargs):
        for key, value in db_kwargs.items():
            if value is not None:
                setattr(self, key, value)

    def get_cfn_attribute(self, attribute_name):
        # Local import to avoid circular dependency with cloudformation.parsing
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Endpoint.Address":
            return self.address
        elif attribute_name == "Endpoint.Port":
            return self.port
        raise UnformattedGetAttTemplateException()

    @staticmethod
    def default_port(engine):
        return {
            "mysql": 3306,
            "mariadb": 3306,
            "postgres": 5432,
            "oracle-ee": 1521,
            "oracle-se2": 1521,
            "oracle-se1": 1521,
            "oracle-se": 1521,
            "sqlserver-ee": 1433,
            "sqlserver-ex": 1433,
            "sqlserver-se": 1433,
            "sqlserver-web": 1433,
        }[engine]

    @staticmethod
    def default_storage_type(iops):
        if iops is None:
            return "gp2"
        else:
            return "io1"

    @staticmethod
    def default_allocated_storage(engine, storage_type):
        return {
            "aurora": {"gp2": 0, "io1": 0, "standard": 0},
            "mysql": {"gp2": 20, "io1": 100, "standard": 5},
            "mariadb": {"gp2": 20, "io1": 100, "standard": 5},
            "postgres": {"gp2": 20, "io1": 100, "standard": 5},
            "oracle-ee": {"gp2": 20, "io1": 100, "standard": 10},
            "oracle-se2": {"gp2": 20, "io1": 100, "standard": 10},
            "oracle-se1": {"gp2": 20, "io1": 100, "standard": 10},
            "oracle-se": {"gp2": 20, "io1": 100, "standard": 10},
            "sqlserver-ee": {"gp2": 200, "io1": 200, "standard": 200},
            "sqlserver-ex": {"gp2": 20, "io1": 100, "standard": 20},
            "sqlserver-se": {"gp2": 200, "io1": 200, "standard": 200},
            "sqlserver-web": {"gp2": 20, "io1": 100, "standard": 20},
        }[engine][storage_type]

    @staticmethod
    def cloudformation_name_type():
        return "DBInstanceIdentifier"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-rds-dbinstance.html
        return "AWS::RDS::DBInstance"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        db_security_groups = properties.get("DBSecurityGroups")
        if not db_security_groups:
            db_security_groups = []
        security_groups = [group.group_name for group in db_security_groups]
        db_subnet_group = properties.get("DBSubnetGroupName")
        db_subnet_group_name = db_subnet_group.subnet_name if db_subnet_group else None
        db_kwargs = {
            "auto_minor_version_upgrade": properties.get("AutoMinorVersionUpgrade"),
            "allocated_storage": properties.get("AllocatedStorage"),
            "availability_zone": properties.get("AvailabilityZone"),
            "backup_retention_period": properties.get("BackupRetentionPeriod"),
            "db_instance_class": properties.get("DBInstanceClass"),
            "db_instance_identifier": resource_name,
            "db_name": properties.get("DBName"),
            "db_subnet_group_name": db_subnet_group_name,
            "engine": properties.get("Engine"),
            "engine_version": properties.get("EngineVersion"),
            "iops": properties.get("Iops"),
            "kms_key_id": properties.get("KmsKeyId"),
            "master_user_password": properties.get("MasterUserPassword"),
            "master_username": properties.get("MasterUsername"),
            "multi_az": properties.get("MultiAZ"),
            "db_parameter_group_name": properties.get("DBParameterGroupName"),
            "port": properties.get("Port", 3306),
            "publicly_accessible": properties.get("PubliclyAccessible"),
            "copy_tags_to_snapshot": properties.get("CopyTagsToSnapshot"),
            "region": region_name,
            "security_groups": security_groups,
            "storage_encrypted": properties.get("StorageEncrypted"),
            "storage_type": properties.get("StorageType"),
            "tags": properties.get("Tags"),
            "vpc_security_group_ids": properties.get("VpcSecurityGroupIds", []),
        }

        rds2_backend = rds2_backends[region_name]
        source_db_identifier = properties.get("SourceDBInstanceIdentifier")
        if source_db_identifier:
            # Replica
            db_kwargs["source_db_identifier"] = source_db_identifier
            database = rds2_backend.create_database_replica(db_kwargs)
        else:
            database = rds2_backend.create_database(db_kwargs)
        return database

    def to_json(self):
        template = Template(
            """{
        "AllocatedStorage": 10,
        "AutoMinorVersionUpgrade": "{{ database.auto_minor_version_upgrade }}",
        "AvailabilityZone": "{{ database.availability_zone }}",
        "BackupRetentionPeriod": "{{ database.backup_retention_period }}",
        "CharacterSetName": {%- if database.character_set_name -%}{{ database.character_set_name }}{%- else %} null{%- endif -%},
        "DBInstanceClass": "{{ database.db_instance_class }}",
        "DBInstanceIdentifier": "{{ database.db_instance_identifier }}",
        "DBInstanceStatus": "{{ database.status }}",
        "DBName": {%- if database.db_name -%}"{{ database.db_name }}"{%- else %} null{%- endif -%},
        {% if database.db_parameter_group_name -%}"DBParameterGroups": {
            "DBParameterGroup": {
            "ParameterApplyStatus": "in-sync",
            "DBParameterGroupName": "{{ database.db_parameter_group_name }}"
          }
        },{%- endif %}
        "DBSecurityGroups": [
          {% for security_group in database.security_groups -%}{%- if loop.index != 1 -%},{%- endif -%}
          {"DBSecurityGroup": {
            "Status": "active",
            "DBSecurityGroupName": "{{ security_group }}"
          }}{% endfor %}
        ],
        {%- if database.db_subnet_group -%}{{ database.db_subnet_group.to_json() }},{%- endif %}
        "Engine": "{{ database.engine }}",
        "EngineVersion": "{{ database.engine_version }}",
        "LatestRestorableTime": null,
        "LicenseModel": "{{ database.license_model }}",
        "MasterUsername": "{{ database.master_username }}",
        "MultiAZ": "{{ database.multi_az }}",{% if database.option_group_name %}
        "OptionGroupMemberships": [{
          "OptionGroupMembership": {
            "OptionGroupName": "{{ database.option_group_name }}",
            "Status": "in-sync"
          }
        }],{%- endif %}
        "PendingModifiedValues": { "MasterUserPassword": "****" },
        "PreferredBackupWindow": "{{ database.preferred_backup_window }}",
        "PreferredMaintenanceWindow": "{{ database.preferred_maintenance_window }}",
        "PubliclyAccessible": "{{ database.publicly_accessible }}",
        "CopyTagsToSnapshot": "{{ database.copy_tags_to_snapshot }}",
        "AllocatedStorage": "{{ database.allocated_storage }}",
        "Endpoint": {
            "Address": "{{ database.address }}",
            "Port": "{{ database.port }}"
        },
        "InstanceCreateTime": "{{ database.instance_create_time }}",
        "Iops": null,
        "ReadReplicaDBInstanceIdentifiers": [{%- for replica in database.replicas -%}
            {%- if not loop.first -%},{%- endif -%}
            "{{ replica }}"
        {%- endfor -%}
        ],
        {%- if database.source_db_identifier -%}
        "ReadReplicaSourceDBInstanceIdentifier": "{{ database.source_db_identifier }}",
        {%- else -%}
        "ReadReplicaSourceDBInstanceIdentifier": null,
        {%- endif -%}
        "SecondaryAvailabilityZone": null,
        "StatusInfos": null,
        "VpcSecurityGroups": [
            {% for vpc_security_group_id in database.vpc_security_group_ids %}
            {
                "Status": "active",
                "VpcSecurityGroupId": "{{ vpc_security_group_id }}"
            }
            {% endfor %}
        ],
        "DBInstanceArn": "{{ database.db_instance_arn }}"
      }"""
        )
        return template.render(database=self)

    def get_tags(self):
        return self.tags

    def add_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def remove_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]

    def delete(self, region_name):
        backend = rds2_backends[region_name]
        backend.delete_database(self.db_instance_identifier)


class Snapshot(BaseModel):

    SUPPORTED_FILTERS = {
        "db-instance-id": FilterDef(
            ["database.db_instance_arn", "database.db_instance_identifier"],
            "DB Instance Identifiers",
        ),
        "db-snapshot-id": FilterDef(["snapshot_id"], "DB Snapshot Identifiers"),
        "dbi-resource-id": FilterDef(["database.dbi_resource_id"], "Dbi Resource Ids"),
        "snapshot-type": FilterDef(None, "Snapshot Types"),
        "engine": FilterDef(["database.engine"], "Engine Names"),
    }

    def __init__(self, database, snapshot_id, tags):
        self.database = database
        self.snapshot_id = snapshot_id
        self.tags = tags
        self.created_at = iso_8601_datetime_with_milliseconds(datetime.datetime.now())

    @property
    def snapshot_arn(self):
        return "arn:aws:rds:{0}:1234567890:snapshot:{1}".format(
            self.database.region, self.snapshot_id
        )

    def to_xml(self):
        template = Template(
            """<DBSnapshot>
              <DBSnapshotIdentifier>{{ snapshot.snapshot_id }}</DBSnapshotIdentifier>
              <DBInstanceIdentifier>{{ database.db_instance_identifier }}</DBInstanceIdentifier>
              <DbiResourceId>{{ database.dbi_resource_id }}</DbiResourceId>
              <SnapshotCreateTime>{{ snapshot.created_at }}</SnapshotCreateTime>
              <Engine>{{ database.engine }}</Engine>
              <AllocatedStorage>{{ database.allocated_storage }}</AllocatedStorage>
              <Status>available</Status>
              <Port>{{ database.port }}</Port>
              <AvailabilityZone>{{ database.availability_zone }}</AvailabilityZone>
              <VpcId>{{ database.db_subnet_group.vpc_id }}</VpcId>
              <InstanceCreateTime>{{ snapshot.created_at }}</InstanceCreateTime>
              <MasterUsername>{{ database.master_username }}</MasterUsername>
              <EngineVersion>{{ database.engine_version }}</EngineVersion>
              <LicenseModel>{{ database.license_model }}</LicenseModel>
              <SnapshotType>manual</SnapshotType>
              {% if database.iops %}
              <Iops>{{ database.iops }}</Iops>
              <StorageType>io1</StorageType>
              {% else %}
              <StorageType>{{ database.storage_type }}</StorageType>
              {% endif %}
              <OptionGroupName>{{ database.option_group_name }}</OptionGroupName>
              <PercentProgress>{{ 100 }}</PercentProgress>
              <SourceRegion>{{ database.region }}</SourceRegion>
              <SourceDBSnapshotIdentifier></SourceDBSnapshotIdentifier>
              <TdeCredentialArn></TdeCredentialArn>
              <Encrypted>{{ database.storage_encrypted }}</Encrypted>
              <KmsKeyId>{{ database.kms_key_id }}</KmsKeyId>
              <DBSnapshotArn>{{ snapshot.snapshot_arn }}</DBSnapshotArn>
              <Timezone></Timezone>
              <IAMDatabaseAuthenticationEnabled>{{ database.enable_iam_database_authentication|lower }}</IAMDatabaseAuthenticationEnabled>
            </DBSnapshot>"""
        )
        return template.render(snapshot=self, database=self.database)

    def get_tags(self):
        return self.tags

    def add_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def remove_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]


class SecurityGroup(CloudFormationModel):
    def __init__(self, group_name, description, tags):
        self.group_name = group_name
        self.description = description
        self.status = "authorized"
        self.ip_ranges = []
        self.ec2_security_groups = []
        self.tags = tags
        self.owner_id = "1234567890"
        self.vpc_id = None

    def to_xml(self):
        template = Template(
            """<DBSecurityGroup>
            <EC2SecurityGroups>
            {% for security_group in security_group.ec2_security_groups %}
                <EC2SecurityGroup>
                    <EC2SecurityGroupId>{{ security_group.id }}</EC2SecurityGroupId>
                    <EC2SecurityGroupName>{{ security_group.name }}</EC2SecurityGroupName>
                    <EC2SecurityGroupOwnerId>{{ security_group.owner_id }}</EC2SecurityGroupOwnerId>
                    <Status>authorized</Status>
                </EC2SecurityGroup>
            {% endfor %}
            </EC2SecurityGroups>

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
        </DBSecurityGroup>"""
        )
        return template.render(security_group=self)

    def to_json(self):
        template = Template(
            """{
            "DBSecurityGroupDescription": "{{ security_group.description }}",
            "DBSecurityGroupName": "{{ security_group.group_name }}",
            "EC2SecurityGroups": {{ security_group.ec2_security_groups }},
            "IPRanges": [{%- for ip in security_group.ip_ranges -%}
                         {%- if loop.index != 1 -%},{%- endif -%}
                         "{{ ip }}"
                         {%- endfor -%}
                        ],
            "OwnerId": "{{ security_group.owner_id }}",
            "VpcId": "{{ security_group.vpc_id }}"
        }"""
        )
        return template.render(security_group=self)

    def authorize_cidr(self, cidr_ip):
        self.ip_ranges.append(cidr_ip)

    def authorize_security_group(self, security_group):
        self.ec2_security_groups.append(security_group)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-rds-dbsecuritygroup.html
        return "AWS::RDS::DBSecurityGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        group_name = resource_name.lower()
        description = properties["GroupDescription"]
        security_group_ingress_rules = properties.get("DBSecurityGroupIngress", [])
        tags = properties.get("Tags")

        ec2_backend = ec2_backends[region_name]
        rds2_backend = rds2_backends[region_name]
        security_group = rds2_backend.create_security_group(
            group_name, description, tags
        )
        for security_group_ingress in security_group_ingress_rules:
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

    def get_tags(self):
        return self.tags

    def add_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def remove_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]

    def delete(self, region_name):
        backend = rds2_backends[region_name]
        backend.delete_security_group(self.group_name)


class SubnetGroup(CloudFormationModel):
    def __init__(self, subnet_name, description, subnets, tags):
        self.subnet_name = subnet_name
        self.description = description
        self.subnets = subnets
        self.status = "Complete"
        self.tags = tags
        self.vpc_id = self.subnets[0].vpc_id

    def to_xml(self):
        template = Template(
            """<DBSubnetGroup>
              <VpcId>{{ subnet_group.vpc_id }}</VpcId>
              <SubnetGroupStatus>{{ subnet_group.status }}</SubnetGroupStatus>
              <DBSubnetGroupDescription>{{ subnet_group.description }}</DBSubnetGroupDescription>
              <DBSubnetGroupName>{{ subnet_group.subnet_name }}</DBSubnetGroupName>
              <Subnets>
                {% for subnet in subnet_group.subnets %}
                <Subnet>
                  <SubnetStatus>Active</SubnetStatus>
                  <SubnetIdentifier>{{ subnet.id }}</SubnetIdentifier>
                  <SubnetAvailabilityZone>
                    <Name>{{ subnet.availability_zone }}</Name>
                    <ProvisionedIopsCapable>false</ProvisionedIopsCapable>
                  </SubnetAvailabilityZone>
                </Subnet>
                {% endfor %}
              </Subnets>
            </DBSubnetGroup>"""
        )
        return template.render(subnet_group=self)

    def to_json(self):
        template = Template(
            """"DBSubnetGroup": {
                "VpcId": "{{ subnet_group.vpc_id }}",
                "SubnetGroupStatus": "{{ subnet_group.status }}",
                "DBSubnetGroupDescription": "{{ subnet_group.description }}",
                "DBSubnetGroupName": "{{ subnet_group.subnet_name }}",
                "Subnets": {
                  "Subnet": [
                    {% for subnet in subnet_group.subnets %}{
                      "SubnetStatus": "Active",
                      "SubnetIdentifier": "{{ subnet.id }}",
                      "SubnetAvailabilityZone": {
                        "Name": "{{ subnet.availability_zone }}",
                        "ProvisionedIopsCapable": "false"
                      }
                    }{%- if not loop.last -%},{%- endif -%}{% endfor %}
                  ]
                }
            }"""
        )
        return template.render(subnet_group=self)

    @staticmethod
    def cloudformation_name_type():
        return "DBSubnetGroupName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-rds-dbsubnetgroup.html
        return "AWS::RDS::DBSubnetGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        description = properties["DBSubnetGroupDescription"]
        subnet_ids = properties["SubnetIds"]
        tags = properties.get("Tags")

        ec2_backend = ec2_backends[region_name]
        subnets = [ec2_backend.get_subnet(subnet_id) for subnet_id in subnet_ids]
        rds2_backend = rds2_backends[region_name]
        subnet_group = rds2_backend.create_subnet_group(
            resource_name, description, subnets, tags
        )
        return subnet_group

    def get_tags(self):
        return self.tags

    def add_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def remove_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]

    def delete(self, region_name):
        backend = rds2_backends[region_name]
        backend.delete_subnet_group(self.subnet_name)


class RDS2Backend(BaseBackend):
    def __init__(self, region):
        self.region = region
        self.arn_regex = re_compile(
            r"^arn:aws:rds:.*:[0-9]*:(db|es|og|pg|ri|secgrp|snapshot|subgrp):.*$"
        )
        self.databases = OrderedDict()
        self.snapshots = OrderedDict()
        self.db_parameter_groups = {}
        self.option_groups = {}
        self.security_groups = {}
        self.subnet_groups = {}

    def reset(self):
        # preserve region
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    def create_database(self, db_kwargs):
        database_id = db_kwargs["db_instance_identifier"]
        database = Database(**db_kwargs)
        self.databases[database_id] = database
        return database

    def create_snapshot(
        self, db_instance_identifier, db_snapshot_identifier, tags=None
    ):
        database = self.databases.get(db_instance_identifier)
        if not database:
            raise DBInstanceNotFoundError(db_instance_identifier)
        if db_snapshot_identifier in self.snapshots:
            raise DBSnapshotAlreadyExistsError(db_snapshot_identifier)
        if len(self.snapshots) >= int(os.environ.get("MOTO_RDS_SNAPSHOT_LIMIT", "100")):
            raise SnapshotQuotaExceededError()
        if tags is None:
            tags = list()
        if database.copy_tags_to_snapshot and not tags:
            tags = database.get_tags()
        snapshot = Snapshot(database, db_snapshot_identifier, tags)
        self.snapshots[db_snapshot_identifier] = snapshot
        return snapshot

    def delete_snapshot(self, db_snapshot_identifier):
        if db_snapshot_identifier not in self.snapshots:
            raise DBSnapshotNotFoundError(db_snapshot_identifier)

        return self.snapshots.pop(db_snapshot_identifier)

    def create_database_replica(self, db_kwargs):
        database_id = db_kwargs["db_instance_identifier"]
        source_database_id = db_kwargs["source_db_identifier"]
        primary = self.find_db_from_id(source_database_id)
        if self.arn_regex.match(source_database_id):
            db_kwargs["region"] = self.region

        # Shouldn't really copy here as the instance is duplicated. RDS replicas have different instances.
        replica = copy.copy(primary)
        replica.update(db_kwargs)
        replica.set_as_replica()
        self.databases[database_id] = replica
        primary.add_replica(replica)
        return replica

    def describe_databases(self, db_instance_identifier=None, filters=None):
        databases = self.databases
        if db_instance_identifier:
            filters = merge_filters(
                filters, {"db-instance-id": [db_instance_identifier]}
            )
        if filters:
            databases = self._filter_resources(databases, filters, Database)
        if db_instance_identifier and not databases:
            raise DBInstanceNotFoundError(db_instance_identifier)
        return list(databases.values())

    def describe_snapshots(
        self, db_instance_identifier, db_snapshot_identifier, filters=None
    ):
        snapshots = self.snapshots
        if db_instance_identifier:
            filters = merge_filters(
                filters, {"db-instance-id": [db_instance_identifier]}
            )
        if db_snapshot_identifier:
            filters = merge_filters(
                filters, {"db-snapshot-id": [db_snapshot_identifier]}
            )
        if filters:
            snapshots = self._filter_resources(snapshots, filters, Snapshot)
        if db_snapshot_identifier and not snapshots and not db_instance_identifier:
            raise DBSnapshotNotFoundError(db_snapshot_identifier)
        return list(snapshots.values())

    def modify_database(self, db_instance_identifier, db_kwargs):
        database = self.describe_databases(db_instance_identifier)[0]
        if "new_db_instance_identifier" in db_kwargs:
            del self.databases[db_instance_identifier]
            db_instance_identifier = db_kwargs[
                "db_instance_identifier"
            ] = db_kwargs.pop("new_db_instance_identifier")
            self.databases[db_instance_identifier] = database
        database.update(db_kwargs)
        return database

    def reboot_db_instance(self, db_instance_identifier):
        database = self.describe_databases(db_instance_identifier)[0]
        return database

    def stop_database(self, db_instance_identifier, db_snapshot_identifier=None):
        database = self.describe_databases(db_instance_identifier)[0]
        # todo: certain rds types not allowed to be stopped at this time.
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StopInstance.html#USER_StopInstance.Limitations
        if database.is_replica or (
            database.multi_az and database.engine.lower().startswith("sqlserver")
        ):
            # todo: more db types not supported by stop/start instance api
            raise InvalidDBClusterStateFaultError(db_instance_identifier)
        if database.status != "available":
            raise InvalidDBInstanceStateError(db_instance_identifier, "stop")
        if db_snapshot_identifier:
            self.create_snapshot(db_instance_identifier, db_snapshot_identifier)
        database.status = "stopped"
        return database

    def start_database(self, db_instance_identifier):
        database = self.describe_databases(db_instance_identifier)[0]
        # todo: bunch of different error messages to be generated from this api call
        if database.status != "stopped":
            raise InvalidDBInstanceStateError(db_instance_identifier, "start")
        database.status = "available"
        return database

    def find_db_from_id(self, db_id):
        if self.arn_regex.match(db_id):
            arn_breakdown = db_id.split(":")
            region = arn_breakdown[3]
            backend = rds2_backends[region]
            db_name = arn_breakdown[-1]
        else:
            backend = self
            db_name = db_id

        return backend.describe_databases(db_name)[0]

    def delete_database(self, db_instance_identifier, db_snapshot_name=None):
        if db_instance_identifier in self.databases:
            if db_snapshot_name:
                self.create_snapshot(db_instance_identifier, db_snapshot_name)
            database = self.databases.pop(db_instance_identifier)
            if database.is_replica:
                primary = self.find_db_from_id(database.source_db_identifier)
                primary.remove_replica(database)
            database.status = "deleting"
            return database
        else:
            raise DBInstanceNotFoundError(db_instance_identifier)

    def create_security_group(self, group_name, description, tags):
        security_group = SecurityGroup(group_name, description, tags)
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

    def delete_db_parameter_group(self, db_parameter_group_name):
        if db_parameter_group_name in self.db_parameter_groups:
            return self.db_parameter_groups.pop(db_parameter_group_name)
        else:
            raise DBParameterGroupNotFoundError(db_parameter_group_name)

    def authorize_security_group(self, security_group_name, cidr_ip):
        security_group = self.describe_security_groups(security_group_name)[0]
        security_group.authorize_cidr(cidr_ip)
        return security_group

    def create_subnet_group(self, subnet_name, description, subnets, tags):
        subnet_group = SubnetGroup(subnet_name, description, subnets, tags)
        self.subnet_groups[subnet_name] = subnet_group
        return subnet_group

    def describe_subnet_groups(self, subnet_group_name):
        if subnet_group_name:
            if subnet_group_name in self.subnet_groups:
                return [self.subnet_groups[subnet_group_name]]
            else:
                raise DBSubnetGroupNotFoundError(subnet_group_name)
        return self.subnet_groups.values()

    def delete_subnet_group(self, subnet_name):
        if subnet_name in self.subnet_groups:
            return self.subnet_groups.pop(subnet_name)
        else:
            raise DBSubnetGroupNotFoundError(subnet_name)

    def create_option_group(self, option_group_kwargs):
        option_group_id = option_group_kwargs["name"]
        valid_option_group_engines = {
            "mariadb": ["10.0", "10.1", "10.2", "10.3"],
            "mysql": ["5.5", "5.6", "5.7", "8.0"],
            "oracle-se2": ["11.2", "12.1", "12.2"],
            "oracle-se1": ["11.2", "12.1", "12.2"],
            "oracle-se": ["11.2", "12.1", "12.2"],
            "oracle-ee": ["11.2", "12.1", "12.2"],
            "sqlserver-se": ["10.50", "11.00"],
            "sqlserver-ee": ["10.50", "11.00"],
            "sqlserver-ex": ["10.50", "11.00"],
            "sqlserver-web": ["10.50", "11.00"],
        }
        if option_group_kwargs["name"] in self.option_groups:
            raise RDSClientError(
                "OptionGroupAlreadyExistsFault",
                "An option group named {0} already exists.".format(
                    option_group_kwargs["name"]
                ),
            )
        if (
            "description" not in option_group_kwargs
            or not option_group_kwargs["description"]
        ):
            raise RDSClientError(
                "InvalidParameterValue",
                "The parameter OptionGroupDescription must be provided and must not be blank.",
            )
        if option_group_kwargs["engine_name"] not in valid_option_group_engines.keys():
            raise RDSClientError(
                "InvalidParameterValue", "Invalid DB engine: non-existent"
            )
        if (
            option_group_kwargs["major_engine_version"]
            not in valid_option_group_engines[option_group_kwargs["engine_name"]]
        ):
            raise RDSClientError(
                "InvalidParameterCombination",
                "Cannot find major version {0} for {1}".format(
                    option_group_kwargs["major_engine_version"],
                    option_group_kwargs["engine_name"],
                ),
            )
        option_group = OptionGroup(**option_group_kwargs)
        self.option_groups[option_group_id] = option_group
        return option_group

    def delete_option_group(self, option_group_name):
        if option_group_name in self.option_groups:
            return self.option_groups.pop(option_group_name)
        else:
            raise OptionGroupNotFoundFaultError(option_group_name)

    def describe_option_groups(self, option_group_kwargs):
        option_group_list = []

        if option_group_kwargs["marker"]:
            marker = option_group_kwargs["marker"]
        else:
            marker = 0
        if option_group_kwargs["max_records"]:
            if (
                option_group_kwargs["max_records"] < 20
                or option_group_kwargs["max_records"] > 100
            ):
                raise RDSClientError(
                    "InvalidParameterValue",
                    "Invalid value for max records. Must be between 20 and 100",
                )
            max_records = option_group_kwargs["max_records"]
        else:
            max_records = 100

        for option_group_name, option_group in self.option_groups.items():
            if (
                option_group_kwargs["name"]
                and option_group.name != option_group_kwargs["name"]
            ):
                continue
            elif (
                option_group_kwargs["engine_name"]
                and option_group.engine_name != option_group_kwargs["engine_name"]
            ):
                continue
            elif (
                option_group_kwargs["major_engine_version"]
                and option_group.major_engine_version
                != option_group_kwargs["major_engine_version"]
            ):
                continue
            else:
                option_group_list.append(option_group)
        if not len(option_group_list):
            raise OptionGroupNotFoundFaultError(option_group_kwargs["name"])
        return option_group_list[marker : max_records + marker]

    @staticmethod
    def describe_option_group_options(engine_name, major_engine_version=None):
        default_option_group_options = {
            "mysql": {
                "5.6": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>5.6</MajorEngineVersion><DefaultPort>11211</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Innodb Memcached for MySQL</Description><Name>MEMCACHED</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>1-4294967295</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies how many memcached read operations (get) to perform before doing a COMMIT to start a new transaction</SettingDescription><SettingName>DAEMON_MEMCACHED_R_BATCH_SIZE</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-4294967295</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies how many memcached write operations, such as add, set, or incr, to perform before doing a COMMIT to start a new transaction</SettingDescription><SettingName>DAEMON_MEMCACHED_W_BATCH_SIZE</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-1073741824</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies how often to auto-commit idle connections that use the InnoDB memcached interface.</SettingDescription><SettingName>INNODB_API_BK_COMMIT_INTERVAL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Disables the use of row locks when using the InnoDB memcached interface.</SettingDescription><SettingName>INNODB_API_DISABLE_ROWLOCK</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Locks the table used by the InnoDB memcached plugin, so that it cannot be dropped or altered by DDL through the SQL interface.</SettingDescription><SettingName>INNODB_API_ENABLE_MDL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0-3</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Lets you control the transaction isolation level on queries processed by the memcached interface.</SettingDescription><SettingName>INNODB_API_TRX_LEVEL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>auto,ascii,binary</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>auto</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>The binding protocol to use which can be either auto, ascii, or binary. The default is auto which means the server automatically negotiates the protocol with the client.</SettingDescription><SettingName>BINDING_PROTOCOL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-2048</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1024</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>The backlog queue configures how many network connections can be waiting to be processed by memcached</SettingDescription><SettingName>BACKLOG_QUEUE_LIMIT</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Disable the use of compare and swap (CAS) which reduces the per-item size by 8 bytes.</SettingDescription><SettingName>CAS_DISABLED</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-48</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>48</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Minimum chunk size in bytes to allocate for the smallest item\'s key, value, and flags. The default is 48 and you can get a significant memory efficiency gain with a lower value.</SettingDescription><SettingName>CHUNK_SIZE</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-2</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1.25</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Chunk size growth factor that controls the size of each successive chunk with each chunk growing times this amount larger than the previous chunk.</SettingDescription><SettingName>CHUNK_SIZE_GROWTH_FACTOR</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>If enabled when there is no more memory to store items, memcached will return an error rather than evicting items.</SettingDescription><SettingName>ERROR_ON_MEMORY_EXHAUSTED</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>10-1024</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1024</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Maximum number of concurrent connections. Setting this value to anything less than 10 prevents MySQL from starting.</SettingDescription><SettingName>MAX_SIMULTANEOUS_CONNECTIONS</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>v,vv,vvv</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>v</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Verbose level for memcached.</SettingDescription><SettingName>VERBOSITY</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>mysql</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
                "all": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>5.6</MajorEngineVersion><DefaultPort>11211</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Innodb Memcached for MySQL</Description><Name>MEMCACHED</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>1-4294967295</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies how many memcached read operations (get) to perform before doing a COMMIT to start a new transaction</SettingDescription><SettingName>DAEMON_MEMCACHED_R_BATCH_SIZE</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-4294967295</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies how many memcached write operations, such as add, set, or incr, to perform before doing a COMMIT to start a new transaction</SettingDescription><SettingName>DAEMON_MEMCACHED_W_BATCH_SIZE</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-1073741824</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies how often to auto-commit idle connections that use the InnoDB memcached interface.</SettingDescription><SettingName>INNODB_API_BK_COMMIT_INTERVAL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Disables the use of row locks when using the InnoDB memcached interface.</SettingDescription><SettingName>INNODB_API_DISABLE_ROWLOCK</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Locks the table used by the InnoDB memcached plugin, so that it cannot be dropped or altered by DDL through the SQL interface.</SettingDescription><SettingName>INNODB_API_ENABLE_MDL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0-3</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Lets you control the transaction isolation level on queries processed by the memcached interface.</SettingDescription><SettingName>INNODB_API_TRX_LEVEL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>auto,ascii,binary</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>auto</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>The binding protocol to use which can be either auto, ascii, or binary. The default is auto which means the server automatically negotiates the protocol with the client.</SettingDescription><SettingName>BINDING_PROTOCOL</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-2048</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1024</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>The backlog queue configures how many network connections can be waiting to be processed by memcached</SettingDescription><SettingName>BACKLOG_QUEUE_LIMIT</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Disable the use of compare and swap (CAS) which reduces the per-item size by 8 bytes.</SettingDescription><SettingName>CAS_DISABLED</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-48</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>48</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Minimum chunk size in bytes to allocate for the smallest item\'s key, value, and flags. The default is 48 and you can get a significant memory efficiency gain with a lower value.</SettingDescription><SettingName>CHUNK_SIZE</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>1-2</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1.25</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Chunk size growth factor that controls the size of each successive chunk with each chunk growing times this amount larger than the previous chunk.</SettingDescription><SettingName>CHUNK_SIZE_GROWTH_FACTOR</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>0,1</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>0</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>If enabled when there is no more memory to store items, memcached will return an error rather than evicting items.</SettingDescription><SettingName>ERROR_ON_MEMORY_EXHAUSTED</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>10-1024</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>1024</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Maximum number of concurrent connections. Setting this value to anything less than 10 prevents MySQL from starting.</SettingDescription><SettingName>MAX_SIMULTANEOUS_CONNECTIONS</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>v,vv,vvv</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>v</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Verbose level for memcached.</SettingDescription><SettingName>VERBOSITY</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>mysql</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
            },
            "oracle-ee": {
                "11.2": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>XMLDB</OptionName></OptionsDependedOn><Description>Oracle Application Express Runtime Environment</Description><Name>APEX</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>APEX</OptionName></OptionsDependedOn><Description>Oracle Application Express Development Environment</Description><Name>APEX-DEV</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Advanced Security - Native Network Encryption</Description><Name>NATIVE_NETWORK_ENCRYPTION</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired encryption behavior</SettingDescription><SettingName>SQLNET.ENCRYPTION_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired data integrity behavior</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of encryption algorithms in order of intended use</SettingDescription><SettingName>SQLNET.ENCRYPTION_TYPES_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>SHA1,MD5</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>SHA1,MD5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of checksumming algorithms in order of intended use</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><DefaultPort>1158</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Oracle Enterprise Manager (Database Control only)</Description><Name>OEM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Statspack</Description><Name>STATSPACK</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - TDE with HSM</Description><Name>TDE_HSM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Change time zone</Description><Name>Timezone</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>Africa/Cairo,Africa/Casablanca,Africa/Harare,Africa/Monrovia,Africa/Nairobi,Africa/Tripoli,Africa/Windhoek,America/Araguaina,America/Asuncion,America/Bogota,America/Caracas,America/Chihuahua,America/Cuiaba,America/Denver,America/Fortaleza,America/Guatemala,America/Halifax,America/Manaus,America/Matamoros,America/Monterrey,America/Montevideo,America/Phoenix,America/Santiago,America/Tijuana,Asia/Amman,Asia/Ashgabat,Asia/Baghdad,Asia/Baku,Asia/Bangkok,Asia/Beirut,Asia/Calcutta,Asia/Damascus,Asia/Dhaka,Asia/Irkutsk,Asia/Jerusalem,Asia/Kabul,Asia/Karachi,Asia/Kathmandu,Asia/Krasnoyarsk,Asia/Magadan,Asia/Muscat,Asia/Novosibirsk,Asia/Riyadh,Asia/Seoul,Asia/Shanghai,Asia/Singapore,Asia/Taipei,Asia/Tehran,Asia/Tokyo,Asia/Ulaanbaatar,Asia/Vladivostok,Asia/Yakutsk,Asia/Yerevan,Atlantic/Azores,Australia/Adelaide,Australia/Brisbane,Australia/Darwin,Australia/Hobart,Australia/Perth,Australia/Sydney,Brazil/East,Canada/Newfoundland,Canada/Saskatchewan,Europe/Amsterdam,Europe/Athens,Europe/Dublin,Europe/Helsinki,Europe/Istanbul,Europe/Kaliningrad,Europe/Moscow,Europe/Paris,Europe/Prague,Europe/Sarajevo,Pacific/Auckland,Pacific/Fiji,Pacific/Guam,Pacific/Honolulu,Pacific/Samoa,US/Alaska,US/Central,US/Eastern,US/East-Indiana,US/Pacific,UTC</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>UTC</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the timezone the user wants to change the system time to</SettingDescription><SettingName>TIME_ZONE</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle XMLDB Repository</Description><Name>XMLDB</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
                "all": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>XMLDB</OptionName></OptionsDependedOn><Description>Oracle Application Express Runtime Environment</Description><Name>APEX</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>APEX</OptionName></OptionsDependedOn><Description>Oracle Application Express Development Environment</Description><Name>APEX-DEV</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Advanced Security - Native Network Encryption</Description><Name>NATIVE_NETWORK_ENCRYPTION</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired encryption behavior</SettingDescription><SettingName>SQLNET.ENCRYPTION_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired data integrity behavior</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of encryption algorithms in order of intended use</SettingDescription><SettingName>SQLNET.ENCRYPTION_TYPES_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>SHA1,MD5</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>SHA1,MD5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of checksumming algorithms in order of intended use</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><DefaultPort>1158</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Oracle Enterprise Manager (Database Control only)</Description><Name>OEM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Statspack</Description><Name>STATSPACK</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - TDE with HSM</Description><Name>TDE_HSM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Change time zone</Description><Name>Timezone</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>Africa/Cairo,Africa/Casablanca,Africa/Harare,Africa/Monrovia,Africa/Nairobi,Africa/Tripoli,Africa/Windhoek,America/Araguaina,America/Asuncion,America/Bogota,America/Caracas,America/Chihuahua,America/Cuiaba,America/Denver,America/Fortaleza,America/Guatemala,America/Halifax,America/Manaus,America/Matamoros,America/Monterrey,America/Montevideo,America/Phoenix,America/Santiago,America/Tijuana,Asia/Amman,Asia/Ashgabat,Asia/Baghdad,Asia/Baku,Asia/Bangkok,Asia/Beirut,Asia/Calcutta,Asia/Damascus,Asia/Dhaka,Asia/Irkutsk,Asia/Jerusalem,Asia/Kabul,Asia/Karachi,Asia/Kathmandu,Asia/Krasnoyarsk,Asia/Magadan,Asia/Muscat,Asia/Novosibirsk,Asia/Riyadh,Asia/Seoul,Asia/Shanghai,Asia/Singapore,Asia/Taipei,Asia/Tehran,Asia/Tokyo,Asia/Ulaanbaatar,Asia/Vladivostok,Asia/Yakutsk,Asia/Yerevan,Atlantic/Azores,Australia/Adelaide,Australia/Brisbane,Australia/Darwin,Australia/Hobart,Australia/Perth,Australia/Sydney,Brazil/East,Canada/Newfoundland,Canada/Saskatchewan,Europe/Amsterdam,Europe/Athens,Europe/Dublin,Europe/Helsinki,Europe/Istanbul,Europe/Kaliningrad,Europe/Moscow,Europe/Paris,Europe/Prague,Europe/Sarajevo,Pacific/Auckland,Pacific/Fiji,Pacific/Guam,Pacific/Honolulu,Pacific/Samoa,US/Alaska,US/Central,US/Eastern,US/East-Indiana,US/Pacific,UTC</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>UTC</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the timezone the user wants to change the system time to</SettingDescription><SettingName>TIME_ZONE</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle XMLDB Repository</Description><Name>XMLDB</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
            },
            "oracle-sa": {
                "11.2": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>XMLDB</OptionName></OptionsDependedOn><Description>Oracle Application Express Runtime Environment</Description><Name>APEX</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>APEX</OptionName></OptionsDependedOn><Description>Oracle Application Express Development Environment</Description><Name>APEX-DEV</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Advanced Security - Native Network Encryption</Description><Name>NATIVE_NETWORK_ENCRYPTION</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired encryption behavior</SettingDescription><SettingName>SQLNET.ENCRYPTION_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired data integrity behavior</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of encryption algorithms in order of intended use</SettingDescription><SettingName>SQLNET.ENCRYPTION_TYPES_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>SHA1,MD5</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>SHA1,MD5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of checksumming algorithms in order of intended use</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><DefaultPort>1158</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Oracle Enterprise Manager (Database Control only)</Description><Name>OEM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Statspack</Description><Name>STATSPACK</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - TDE with HSM</Description><Name>TDE_HSM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Change time zone</Description><Name>Timezone</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>Africa/Cairo,Africa/Casablanca,Africa/Harare,Africa/Monrovia,Africa/Nairobi,Africa/Tripoli,Africa/Windhoek,America/Araguaina,America/Asuncion,America/Bogota,America/Caracas,America/Chihuahua,America/Cuiaba,America/Denver,America/Fortaleza,America/Guatemala,America/Halifax,America/Manaus,America/Matamoros,America/Monterrey,America/Montevideo,America/Phoenix,America/Santiago,America/Tijuana,Asia/Amman,Asia/Ashgabat,Asia/Baghdad,Asia/Baku,Asia/Bangkok,Asia/Beirut,Asia/Calcutta,Asia/Damascus,Asia/Dhaka,Asia/Irkutsk,Asia/Jerusalem,Asia/Kabul,Asia/Karachi,Asia/Kathmandu,Asia/Krasnoyarsk,Asia/Magadan,Asia/Muscat,Asia/Novosibirsk,Asia/Riyadh,Asia/Seoul,Asia/Shanghai,Asia/Singapore,Asia/Taipei,Asia/Tehran,Asia/Tokyo,Asia/Ulaanbaatar,Asia/Vladivostok,Asia/Yakutsk,Asia/Yerevan,Atlantic/Azores,Australia/Adelaide,Australia/Brisbane,Australia/Darwin,Australia/Hobart,Australia/Perth,Australia/Sydney,Brazil/East,Canada/Newfoundland,Canada/Saskatchewan,Europe/Amsterdam,Europe/Athens,Europe/Dublin,Europe/Helsinki,Europe/Istanbul,Europe/Kaliningrad,Europe/Moscow,Europe/Paris,Europe/Prague,Europe/Sarajevo,Pacific/Auckland,Pacific/Fiji,Pacific/Guam,Pacific/Honolulu,Pacific/Samoa,US/Alaska,US/Central,US/Eastern,US/East-Indiana,US/Pacific,UTC</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>UTC</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the timezone the user wants to change the system time to</SettingDescription><SettingName>TIME_ZONE</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle XMLDB Repository</Description><Name>XMLDB</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
                "all": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>XMLDB</OptionName></OptionsDependedOn><Description>Oracle Application Express Runtime Environment</Description><Name>APEX</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>APEX</OptionName></OptionsDependedOn><Description>Oracle Application Express Development Environment</Description><Name>APEX-DEV</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Advanced Security - Native Network Encryption</Description><Name>NATIVE_NETWORK_ENCRYPTION</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired encryption behavior</SettingDescription><SettingName>SQLNET.ENCRYPTION_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired data integrity behavior</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of encryption algorithms in order of intended use</SettingDescription><SettingName>SQLNET.ENCRYPTION_TYPES_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>SHA1,MD5</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>SHA1,MD5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of checksumming algorithms in order of intended use</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><DefaultPort>1158</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Oracle Enterprise Manager (Database Control only)</Description><Name>OEM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Statspack</Description><Name>STATSPACK</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - TDE with HSM</Description><Name>TDE_HSM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Change time zone</Description><Name>Timezone</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>Africa/Cairo,Africa/Casablanca,Africa/Harare,Africa/Monrovia,Africa/Nairobi,Africa/Tripoli,Africa/Windhoek,America/Araguaina,America/Asuncion,America/Bogota,America/Caracas,America/Chihuahua,America/Cuiaba,America/Denver,America/Fortaleza,America/Guatemala,America/Halifax,America/Manaus,America/Matamoros,America/Monterrey,America/Montevideo,America/Phoenix,America/Santiago,America/Tijuana,Asia/Amman,Asia/Ashgabat,Asia/Baghdad,Asia/Baku,Asia/Bangkok,Asia/Beirut,Asia/Calcutta,Asia/Damascus,Asia/Dhaka,Asia/Irkutsk,Asia/Jerusalem,Asia/Kabul,Asia/Karachi,Asia/Kathmandu,Asia/Krasnoyarsk,Asia/Magadan,Asia/Muscat,Asia/Novosibirsk,Asia/Riyadh,Asia/Seoul,Asia/Shanghai,Asia/Singapore,Asia/Taipei,Asia/Tehran,Asia/Tokyo,Asia/Ulaanbaatar,Asia/Vladivostok,Asia/Yakutsk,Asia/Yerevan,Atlantic/Azores,Australia/Adelaide,Australia/Brisbane,Australia/Darwin,Australia/Hobart,Australia/Perth,Australia/Sydney,Brazil/East,Canada/Newfoundland,Canada/Saskatchewan,Europe/Amsterdam,Europe/Athens,Europe/Dublin,Europe/Helsinki,Europe/Istanbul,Europe/Kaliningrad,Europe/Moscow,Europe/Paris,Europe/Prague,Europe/Sarajevo,Pacific/Auckland,Pacific/Fiji,Pacific/Guam,Pacific/Honolulu,Pacific/Samoa,US/Alaska,US/Central,US/Eastern,US/East-Indiana,US/Pacific,UTC</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>UTC</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the timezone the user wants to change the system time to</SettingDescription><SettingName>TIME_ZONE</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle XMLDB Repository</Description><Name>XMLDB</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
            },
            "oracle-sa1": {
                "11.2": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>XMLDB</OptionName></OptionsDependedOn><Description>Oracle Application Express Runtime Environment</Description><Name>APEX</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>APEX</OptionName></OptionsDependedOn><Description>Oracle Application Express Development Environment</Description><Name>APEX-DEV</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Advanced Security - Native Network Encryption</Description><Name>NATIVE_NETWORK_ENCRYPTION</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired encryption behavior</SettingDescription><SettingName>SQLNET.ENCRYPTION_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired data integrity behavior</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of encryption algorithms in order of intended use</SettingDescription><SettingName>SQLNET.ENCRYPTION_TYPES_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>SHA1,MD5</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>SHA1,MD5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of checksumming algorithms in order of intended use</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><DefaultPort>1158</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Oracle Enterprise Manager (Database Control only)</Description><Name>OEM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Statspack</Description><Name>STATSPACK</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - TDE with HSM</Description><Name>TDE_HSM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Change time zone</Description><Name>Timezone</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>Africa/Cairo,Africa/Casablanca,Africa/Harare,Africa/Monrovia,Africa/Nairobi,Africa/Tripoli,Africa/Windhoek,America/Araguaina,America/Asuncion,America/Bogota,America/Caracas,America/Chihuahua,America/Cuiaba,America/Denver,America/Fortaleza,America/Guatemala,America/Halifax,America/Manaus,America/Matamoros,America/Monterrey,America/Montevideo,America/Phoenix,America/Santiago,America/Tijuana,Asia/Amman,Asia/Ashgabat,Asia/Baghdad,Asia/Baku,Asia/Bangkok,Asia/Beirut,Asia/Calcutta,Asia/Damascus,Asia/Dhaka,Asia/Irkutsk,Asia/Jerusalem,Asia/Kabul,Asia/Karachi,Asia/Kathmandu,Asia/Krasnoyarsk,Asia/Magadan,Asia/Muscat,Asia/Novosibirsk,Asia/Riyadh,Asia/Seoul,Asia/Shanghai,Asia/Singapore,Asia/Taipei,Asia/Tehran,Asia/Tokyo,Asia/Ulaanbaatar,Asia/Vladivostok,Asia/Yakutsk,Asia/Yerevan,Atlantic/Azores,Australia/Adelaide,Australia/Brisbane,Australia/Darwin,Australia/Hobart,Australia/Perth,Australia/Sydney,Brazil/East,Canada/Newfoundland,Canada/Saskatchewan,Europe/Amsterdam,Europe/Athens,Europe/Dublin,Europe/Helsinki,Europe/Istanbul,Europe/Kaliningrad,Europe/Moscow,Europe/Paris,Europe/Prague,Europe/Sarajevo,Pacific/Auckland,Pacific/Fiji,Pacific/Guam,Pacific/Honolulu,Pacific/Samoa,US/Alaska,US/Central,US/Eastern,US/East-Indiana,US/Pacific,UTC</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>UTC</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the timezone the user wants to change the system time to</SettingDescription><SettingName>TIME_ZONE</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle XMLDB Repository</Description><Name>XMLDB</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
                "all": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>XMLDB</OptionName></OptionsDependedOn><Description>Oracle Application Express Runtime Environment</Description><Name>APEX</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn><OptionName>APEX</OptionName></OptionsDependedOn><Description>Oracle Application Express Development Environment</Description><Name>APEX-DEV</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Advanced Security - Native Network Encryption</Description><Name>NATIVE_NETWORK_ENCRYPTION</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired encryption behavior</SettingDescription><SettingName>SQLNET.ENCRYPTION_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>ACCEPTED,REJECTED,REQUESTED,REQUIRED</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>REQUESTED</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the desired data integrity behavior</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>RC4_256,AES256,AES192,3DES168,RC4_128,AES128,3DES112,RC4_56,DES,RC4_40,DES40</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of encryption algorithms in order of intended use</SettingDescription><SettingName>SQLNET.ENCRYPTION_TYPES_SERVER</SettingName></OptionGroupOptionSetting><OptionGroupOptionSetting><AllowedValues>SHA1,MD5</AllowedValues><ApplyType>STATIC</ApplyType><DefaultValue>SHA1,MD5</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies list of checksumming algorithms in order of intended use</SettingDescription><SettingName>SQLNET.CRYPTO_CHECKSUM_TYPES_SERVER</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><DefaultPort>1158</DefaultPort><PortRequired>True</PortRequired><OptionsDependedOn></OptionsDependedOn><Description>Oracle Enterprise Manager (Database Control only)</Description><Name>OEM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle Statspack</Description><Name>STATSPACK</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Oracle Advanced Security - TDE with HSM</Description><Name>TDE_HSM</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Permanent>True</Permanent><Description>Change time zone</Description><Name>Timezone</Name><OptionGroupOptionSettings><OptionGroupOptionSetting><AllowedValues>Africa/Cairo,Africa/Casablanca,Africa/Harare,Africa/Monrovia,Africa/Nairobi,Africa/Tripoli,Africa/Windhoek,America/Araguaina,America/Asuncion,America/Bogota,America/Caracas,America/Chihuahua,America/Cuiaba,America/Denver,America/Fortaleza,America/Guatemala,America/Halifax,America/Manaus,America/Matamoros,America/Monterrey,America/Montevideo,America/Phoenix,America/Santiago,America/Tijuana,Asia/Amman,Asia/Ashgabat,Asia/Baghdad,Asia/Baku,Asia/Bangkok,Asia/Beirut,Asia/Calcutta,Asia/Damascus,Asia/Dhaka,Asia/Irkutsk,Asia/Jerusalem,Asia/Kabul,Asia/Karachi,Asia/Kathmandu,Asia/Krasnoyarsk,Asia/Magadan,Asia/Muscat,Asia/Novosibirsk,Asia/Riyadh,Asia/Seoul,Asia/Shanghai,Asia/Singapore,Asia/Taipei,Asia/Tehran,Asia/Tokyo,Asia/Ulaanbaatar,Asia/Vladivostok,Asia/Yakutsk,Asia/Yerevan,Atlantic/Azores,Australia/Adelaide,Australia/Brisbane,Australia/Darwin,Australia/Hobart,Australia/Perth,Australia/Sydney,Brazil/East,Canada/Newfoundland,Canada/Saskatchewan,Europe/Amsterdam,Europe/Athens,Europe/Dublin,Europe/Helsinki,Europe/Istanbul,Europe/Kaliningrad,Europe/Moscow,Europe/Paris,Europe/Prague,Europe/Sarajevo,Pacific/Auckland,Pacific/Fiji,Pacific/Guam,Pacific/Honolulu,Pacific/Samoa,US/Alaska,US/Central,US/Eastern,US/East-Indiana,US/Pacific,UTC</AllowedValues><ApplyType>DYNAMIC</ApplyType><DefaultValue>UTC</DefaultValue><IsModifiable>True</IsModifiable><SettingDescription>Specifies the timezone the user wants to change the system time to</SettingDescription><SettingName>TIME_ZONE</SettingName></OptionGroupOptionSetting></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.2</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>Oracle XMLDB Repository</Description><Name>XMLDB</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>oracle-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
            },
            "sqlserver-ee": {
                "10.50": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>10.50</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>SQLServer Database Mirroring</Description><Name>Mirroring</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>10.50</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Description>SQL Server - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
                "11.00": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>11.00</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>SQLServer Database Mirroring</Description><Name>Mirroring</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.00</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Description>SQL Server - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
                "all": '<DescribeOptionGroupOptionsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">\n  <DescribeOptionGroupOptionsResult>\n    <OptionGroupOptions>\n    \n      <OptionGroupOption><MajorEngineVersion>10.50</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>SQLServer Database Mirroring</Description><Name>Mirroring</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>10.50</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Description>SQL Server - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.00</MajorEngineVersion><OptionsDependedOn></OptionsDependedOn><Description>SQLServer Database Mirroring</Description><Name>Mirroring</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n      <OptionGroupOption><MajorEngineVersion>11.00</MajorEngineVersion><Persistent>True</Persistent><OptionsDependedOn></OptionsDependedOn><Description>SQL Server - Transparent Data Encryption</Description><Name>TDE</Name><OptionGroupOptionSettings></OptionGroupOptionSettings><EngineName>sqlserver-ee</EngineName></OptionGroupOption>\n    \n    </OptionGroupOptions>\n  </DescribeOptionGroupOptionsResult>\n  <ResponseMetadata>\n    <RequestId>457f7bb8-9fbf-11e4-9084-5754f80d5144</RequestId>\n  </ResponseMetadata>\n</DescribeOptionGroupOptionsResponse>',
            },
        }

        if engine_name not in default_option_group_options:
            raise RDSClientError(
                "InvalidParameterValue", "Invalid DB engine: {0}".format(engine_name)
            )
        if (
            major_engine_version
            and major_engine_version not in default_option_group_options[engine_name]
        ):
            raise RDSClientError(
                "InvalidParameterCombination",
                "Cannot find major version {0} for {1}".format(
                    major_engine_version, engine_name
                ),
            )
        if major_engine_version:
            return default_option_group_options[engine_name][major_engine_version]
        return default_option_group_options[engine_name]["all"]

    def modify_option_group(
        self,
        option_group_name,
        options_to_include=None,
        options_to_remove=None,
        apply_immediately=None,
    ):
        if option_group_name not in self.option_groups:
            raise OptionGroupNotFoundFaultError(option_group_name)
        if not options_to_include and not options_to_remove:
            raise RDSClientError(
                "InvalidParameterValue",
                "At least one option must be added, modified, or removed.",
            )
        if options_to_remove:
            self.option_groups[option_group_name].remove_options(options_to_remove)
        if options_to_include:
            self.option_groups[option_group_name].add_options(options_to_include)
        return self.option_groups[option_group_name]

    def create_db_parameter_group(self, db_parameter_group_kwargs):
        db_parameter_group_id = db_parameter_group_kwargs["name"]
        if db_parameter_group_kwargs["name"] in self.db_parameter_groups:
            raise RDSClientError(
                "DBParameterGroupAlreadyExistsFault",
                "A DB parameter group named {0} already exists.".format(
                    db_parameter_group_kwargs["name"]
                ),
            )
        if not db_parameter_group_kwargs.get("description"):
            raise RDSClientError(
                "InvalidParameterValue",
                "The parameter Description must be provided and must not be blank.",
            )
        if not db_parameter_group_kwargs.get("family"):
            raise RDSClientError(
                "InvalidParameterValue",
                "The parameter DBParameterGroupName must be provided and must not be blank.",
            )
        db_parameter_group_kwargs["region"] = self.region
        db_parameter_group = DBParameterGroup(**db_parameter_group_kwargs)
        self.db_parameter_groups[db_parameter_group_id] = db_parameter_group
        return db_parameter_group

    def describe_db_parameter_groups(self, db_parameter_group_kwargs):
        db_parameter_group_list = []

        if db_parameter_group_kwargs.get("marker"):
            marker = db_parameter_group_kwargs["marker"]
        else:
            marker = 0
        if db_parameter_group_kwargs.get("max_records"):
            if (
                db_parameter_group_kwargs["max_records"] < 20
                or db_parameter_group_kwargs["max_records"] > 100
            ):
                raise RDSClientError(
                    "InvalidParameterValue",
                    "Invalid value for max records. Must be between 20 and 100",
                )
            max_records = db_parameter_group_kwargs["max_records"]
        else:
            max_records = 100

        for (
            db_parameter_group_name,
            db_parameter_group,
        ) in self.db_parameter_groups.items():
            if not db_parameter_group_kwargs.get(
                "name"
            ) or db_parameter_group.name == db_parameter_group_kwargs.get("name"):
                db_parameter_group_list.append(db_parameter_group)
            else:
                continue

        return db_parameter_group_list[marker : max_records + marker]

    def modify_db_parameter_group(
        self, db_parameter_group_name, db_parameter_group_parameters
    ):
        if db_parameter_group_name not in self.db_parameter_groups:
            raise DBParameterGroupNotFoundError(db_parameter_group_name)

        db_parameter_group = self.db_parameter_groups[db_parameter_group_name]
        db_parameter_group.update_parameters(db_parameter_group_parameters)

        return db_parameter_group

    def list_tags_for_resource(self, arn):
        if self.arn_regex.match(arn):
            arn_breakdown = arn.split(":")
            resource_type = arn_breakdown[len(arn_breakdown) - 2]
            resource_name = arn_breakdown[len(arn_breakdown) - 1]
            if resource_type == "db":  # Database
                if resource_name in self.databases:
                    return self.databases[resource_name].get_tags()
            elif resource_type == "es":  # Event Subscription
                # TODO: Complete call to tags on resource type Event
                # Subscription
                return []
            elif resource_type == "og":  # Option Group
                if resource_name in self.option_groups:
                    return self.option_groups[resource_name].get_tags()
            elif resource_type == "pg":  # Parameter Group
                if resource_name in self.db_parameter_groups:
                    return self.db_parameter_groups[resource_name].get_tags()
            elif resource_type == "ri":  # Reserved DB instance
                # TODO: Complete call to tags on resource type Reserved DB
                # instance
                return []
            elif resource_type == "secgrp":  # DB security group
                if resource_name in self.security_groups:
                    return self.security_groups[resource_name].get_tags()
            elif resource_type == "snapshot":  # DB Snapshot
                if resource_name in self.snapshots:
                    return self.snapshots[resource_name].get_tags()
            elif resource_type == "subgrp":  # DB subnet group
                if resource_name in self.subnet_groups:
                    return self.subnet_groups[resource_name].get_tags()
        else:
            raise RDSClientError(
                "InvalidParameterValue", "Invalid resource name: {0}".format(arn)
            )
        return []

    def remove_tags_from_resource(self, arn, tag_keys):
        if self.arn_regex.match(arn):
            arn_breakdown = arn.split(":")
            resource_type = arn_breakdown[len(arn_breakdown) - 2]
            resource_name = arn_breakdown[len(arn_breakdown) - 1]
            if resource_type == "db":  # Database
                if resource_name in self.databases:
                    self.databases[resource_name].remove_tags(tag_keys)
            elif resource_type == "es":  # Event Subscription
                return None
            elif resource_type == "og":  # Option Group
                if resource_name in self.option_groups:
                    return self.option_groups[resource_name].remove_tags(tag_keys)
            elif resource_type == "pg":  # Parameter Group
                return None
            elif resource_type == "ri":  # Reserved DB instance
                return None
            elif resource_type == "secgrp":  # DB security group
                if resource_name in self.security_groups:
                    return self.security_groups[resource_name].remove_tags(tag_keys)
            elif resource_type == "snapshot":  # DB Snapshot
                if resource_name in self.snapshots:
                    return self.snapshots[resource_name].remove_tags(tag_keys)
            elif resource_type == "subgrp":  # DB subnet group
                if resource_name in self.subnet_groups:
                    return self.subnet_groups[resource_name].remove_tags(tag_keys)
        else:
            raise RDSClientError(
                "InvalidParameterValue", "Invalid resource name: {0}".format(arn)
            )

    def add_tags_to_resource(self, arn, tags):
        if self.arn_regex.match(arn):
            arn_breakdown = arn.split(":")
            resource_type = arn_breakdown[len(arn_breakdown) - 2]
            resource_name = arn_breakdown[len(arn_breakdown) - 1]
            if resource_type == "db":  # Database
                if resource_name in self.databases:
                    return self.databases[resource_name].add_tags(tags)
            elif resource_type == "es":  # Event Subscription
                return []
            elif resource_type == "og":  # Option Group
                if resource_name in self.option_groups:
                    return self.option_groups[resource_name].add_tags(tags)
            elif resource_type == "pg":  # Parameter Group
                return []
            elif resource_type == "ri":  # Reserved DB instance
                return []
            elif resource_type == "secgrp":  # DB security group
                if resource_name in self.security_groups:
                    return self.security_groups[resource_name].add_tags(tags)
            elif resource_type == "snapshot":  # DB Snapshot
                if resource_name in self.snapshots:
                    return self.snapshots[resource_name].add_tags(tags)
            elif resource_type == "subgrp":  # DB subnet group
                if resource_name in self.subnet_groups:
                    return self.subnet_groups[resource_name].add_tags(tags)
        else:
            raise RDSClientError(
                "InvalidParameterValue", "Invalid resource name: {0}".format(arn)
            )

    @staticmethod
    def _filter_resources(resources, filters, resource_class):
        try:
            filter_defs = resource_class.SUPPORTED_FILTERS
            validate_filters(filters, filter_defs)
            return apply_filter(resources, filters, filter_defs)
        except KeyError as e:
            # https://stackoverflow.com/questions/24998968/why-does-strkeyerror-add-extra-quotes
            raise InvalidParameterValue(e.args[0])
        except ValueError as e:
            raise InvalidParameterCombination(str(e))


class OptionGroup(object):
    def __init__(self, name, engine_name, major_engine_version, description=None):
        self.engine_name = engine_name
        self.major_engine_version = major_engine_version
        self.description = description
        self.name = name
        self.vpc_and_non_vpc_instance_memberships = False
        self.options = {}
        self.vpcId = "null"
        self.tags = []

    def to_json(self):
        template = Template(
            """{
    "VpcId": null,
    "MajorEngineVersion": "{{ option_group.major_engine_version }}",
    "OptionGroupDescription": "{{ option_group.description }}",
    "AllowsVpcAndNonVpcInstanceMemberships": "{{ option_group.vpc_and_non_vpc_instance_memberships }}",
    "EngineName": "{{ option_group.engine_name }}",
    "Options": [],
    "OptionGroupName": "{{ option_group.name }}"
}"""
        )
        return template.render(option_group=self)

    def to_xml(self):
        template = Template(
            """<OptionGroup>
          <OptionGroupName>{{ option_group.name }}</OptionGroupName>
          <AllowsVpcAndNonVpcInstanceMemberships>{{ option_group.vpc_and_non_vpc_instance_memberships }}</AllowsVpcAndNonVpcInstanceMemberships>
          <MajorEngineVersion>{{ option_group.major_engine_version }}</MajorEngineVersion>
          <EngineName>{{ option_group.engine_name }}</EngineName>
          <OptionGroupDescription>{{ option_group.description }}</OptionGroupDescription>
          <Options/>
        </OptionGroup>"""
        )
        return template.render(option_group=self)

    def remove_options(self, options_to_remove):
        # TODO: Check for option in self.options and remove if exists. Raise
        # error otherwise
        return

    def add_options(self, options_to_add):
        # TODO: Validate option and add it to self.options. If invalid raise
        # error
        return

    def get_tags(self):
        return self.tags

    def add_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def remove_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]


class OptionGroupOption(object):
    def __init__(self, **kwargs):
        self.default_port = kwargs.get("default_port")
        self.description = kwargs.get("description")
        self.engine_name = kwargs.get("engine_name")
        self.major_engine_version = kwargs.get("major_engine_version")
        self.name = kwargs.get("name")
        self.option_group_option_settings = self._make_option_group_option_settings(
            kwargs.get("option_group_option_settings", [])
        )
        self.options_depended_on = kwargs.get("options_depended_on", [])
        self.permanent = kwargs.get("permanent")
        self.persistent = kwargs.get("persistent")
        self.port_required = kwargs.get("port_required")

    def _make_option_group_option_settings(self, option_group_option_settings_kwargs):
        return [
            OptionGroupOptionSetting(**setting_kwargs)
            for setting_kwargs in option_group_option_settings_kwargs
        ]

    def to_json(self):
        template = Template(
            """{ "MinimumRequiredMinorEngineVersion":
            "2789.0.v1",
            "OptionsDependedOn": [],
            "MajorEngineVersion": "10.50",
            "Persistent": false,
            "DefaultPort": null,
            "Permanent": false,
            "OptionGroupOptionSettings": [],
            "EngineName": "sqlserver-se",
            "Name": "Mirroring",
            "PortRequired": false,
            "Description": "SQLServer Database Mirroring"
        }"""
        )
        return template.render(option_group=self)

    def to_xml(self):
        template = Template(
            """<OptionGroupOption>
    <MajorEngineVersion>{{ option_group.major_engine_version }}</MajorEngineVersion>
    <DefaultPort>{{ option_group.default_port }}</DefaultPort>
    <PortRequired>{{ option_group.port_required }}</PortRequired>
    <Persistent>{{ option_group.persistent }}</Persistent>
    <OptionsDependedOn>
    {%- for option_name in option_group.options_depended_on -%}
      <OptionName>{{ option_name }}</OptionName>
    {%- endfor -%}
    </OptionsDependedOn>
    <Permanent>{{ option_group.permanent }}</Permanent>
    <Description>{{ option_group.description }}</Description>
    <Name>{{ option_group.name }}</Name>
    <OptionGroupOptionSettings>
    {%- for setting in option_group.option_group_option_settings -%}
      {{ setting.to_xml() }}
    {%- endfor -%}
    </OptionGroupOptionSettings>
    <EngineName>{{ option_group.engine_name }}</EngineName>
    <MinimumRequiredMinorEngineVersion>{{ option_group.minimum_required_minor_engine_version }}</MinimumRequiredMinorEngineVersion>
</OptionGroupOption>"""
        )
        return template.render(option_group=self)


class OptionGroupOptionSetting(object):
    def __init__(self, *kwargs):
        self.allowed_values = kwargs.get("allowed_values")
        self.apply_type = kwargs.get("apply_type")
        self.default_value = kwargs.get("default_value")
        self.is_modifiable = kwargs.get("is_modifiable")
        self.setting_description = kwargs.get("setting_description")
        self.setting_name = kwargs.get("setting_name")

    def to_xml(self):
        template = Template(
            """<OptionGroupOptionSetting>
    <AllowedValues>{{ option_group_option_setting.allowed_values }}</AllowedValues>
    <ApplyType>{{ option_group_option_setting.apply_type }}</ApplyType>
    <DefaultValue>{{ option_group_option_setting.default_value }}</DefaultValue>
    <IsModifiable>{{ option_group_option_setting.is_modifiable }}</IsModifiable>
    <SettingDescription>{{ option_group_option_setting.setting_description }}</SettingDescription>
    <SettingName>{{ option_group_option_setting.setting_name }}</SettingName>
</OptionGroupOptionSetting>"""
        )
        return template.render(option_group_option_setting=self)


def make_rds_arn(region, name):
    return "arn:aws:rds:{0}:{1}:pg:{2}".format(region, ACCOUNT_ID, name)


class DBParameterGroup(CloudFormationModel):
    def __init__(self, name, description, family, tags, region):
        self.name = name
        self.description = description
        self.family = family
        self.tags = tags
        self.parameters = defaultdict(dict)
        self.arn = make_rds_arn(region, name)

    def to_xml(self):
        template = Template(
            """<DBParameterGroup>
          <DBParameterGroupName>{{ param_group.name }}</DBParameterGroupName>
          <DBParameterGroupFamily>{{ param_group.family }}</DBParameterGroupFamily>
          <Description>{{ param_group.description }}</Description>
          <DBParameterGroupArn>{{ param_group.arn }}</DBParameterGroupArn>
        </DBParameterGroup>"""
        )
        return template.render(param_group=self)

    def get_tags(self):
        return self.tags

    def add_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def remove_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]

    def update_parameters(self, new_parameters):
        for new_parameter in new_parameters:
            parameter = self.parameters[new_parameter["ParameterName"]]
            parameter.update(new_parameter)

    def delete(self, region_name):
        backend = rds2_backends[region_name]
        backend.delete_db_parameter_group(self.name)

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-rds-dbparametergroup.html
        return "AWS::RDS::DBParameterGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        db_parameter_group_kwargs = {
            "description": properties["Description"],
            "family": properties["Family"],
            "name": resource_name.lower(),
            "tags": properties.get("Tags"),
        }
        db_parameter_group_parameters = []
        for db_parameter, db_parameter_value in properties.get(
            "Parameters", {}
        ).items():
            db_parameter_group_parameters.append(
                {"ParameterName": db_parameter, "ParameterValue": db_parameter_value}
            )

        rds2_backend = rds2_backends[region_name]
        db_parameter_group = rds2_backend.create_db_parameter_group(
            db_parameter_group_kwargs
        )
        db_parameter_group.update_parameters(db_parameter_group_parameters)
        return db_parameter_group


rds2_backends = {}
for region in Session().get_available_regions("rds"):
    rds2_backends[region] = RDS2Backend(region)
for region in Session().get_available_regions("rds", partition_name="aws-us-gov"):
    rds2_backends[region] = RDS2Backend(region)
for region in Session().get_available_regions("rds", partition_name="aws-cn"):
    rds2_backends[region] = RDS2Backend(region)
