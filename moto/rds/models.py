from __future__ import unicode_literals

import boto.rds
from jinja2 import Template

from moto.cloudformation.exceptions import UnformattedGetAttTemplateException
from moto.core import BaseBackend, BaseModel
from moto.core.utils import get_random_hex
from moto.ec2.models import ec2_backends
from moto.rds2.models import rds2_backends


class Database(BaseModel):
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

        db_instance_identifier = properties.get("DBInstanceIdentifier")
        if not db_instance_identifier:
            db_instance_identifier = resource_name.lower() + get_random_hex(12)
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
            "db_instance_identifier": db_instance_identifier,
            "db_name": properties.get("DBName"),
            "db_subnet_group_name": db_subnet_group_name,
            "engine": properties.get("Engine"),
            "engine_version": properties.get("EngineVersion"),
            "iops": properties.get("Iops"),
            "kms_key_id": properties.get("KmsKeyId"),
            "master_password": properties.get("MasterUserPassword"),
            "master_username": properties.get("MasterUsername"),
            "multi_az": properties.get("MultiAZ"),
            "port": properties.get("Port", 3306),
            "publicly_accessible": properties.get("PubliclyAccessible"),
            "copy_tags_to_snapshot": properties.get("CopyTagsToSnapshot"),
            "region": region_name,
            "security_groups": security_groups,
            "storage_encrypted": properties.get("StorageEncrypted"),
            "storage_type": properties.get("StorageType"),
            "tags": properties.get("Tags"),
        }

        rds_backend = rds_backends[region_name]
        source_db_identifier = properties.get("SourceDBInstanceIdentifier")
        if source_db_identifier:
            # Replica
            db_kwargs["source_db_identifier"] = source_db_identifier
            database = rds_backend.create_database_replica(db_kwargs)
        else:
            database = rds_backend.create_database(db_kwargs)
        return database

    def to_xml(self):
        template = Template(
            """<DBInstance>
              <BackupRetentionPeriod>{{ database.backup_retention_period }}</BackupRetentionPeriod>
              <DBInstanceStatus>{{ database.status }}</DBInstanceStatus>
              <MultiAZ>{{ database.multi_az }}</MultiAZ>
              <VpcSecurityGroups/>
              <DBInstanceIdentifier>{{ database.db_instance_identifier }}</DBInstanceIdentifier>
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
              <LicenseModel>{{ database.license_model }}</LicenseModel>
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
              <InstanceCreateTime>{{ database.instance_create_time }}</InstanceCreateTime>
              <MasterUsername>{{ database.master_username }}</MasterUsername>
              <Endpoint>
                <Address>{{ database.address }}</Address>
                <Port>{{ database.port }}</Port>
              </Endpoint>
              <DBInstanceArn>{{ database.db_instance_arn }}</DBInstanceArn>
            </DBInstance>"""
        )
        return template.render(database=self)

    def delete(self, region_name):
        backend = rds_backends[region_name]
        backend.delete_database(self.db_instance_identifier)


class SecurityGroup(BaseModel):
    def __init__(self, group_name, description):
        self.group_name = group_name
        self.description = description
        self.status = "authorized"
        self.ip_ranges = []
        self.ec2_security_groups = []

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

    def authorize_cidr(self, cidr_ip):
        self.ip_ranges.append(cidr_ip)

    def authorize_security_group(self, security_group):
        self.ec2_security_groups.append(security_group)

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]
        group_name = resource_name.lower() + get_random_hex(12)
        description = properties["GroupDescription"]
        security_group_ingress_rules = properties.get("DBSecurityGroupIngress", [])
        tags = properties.get("Tags")

        ec2_backend = ec2_backends[region_name]
        rds_backend = rds_backends[region_name]
        security_group = rds_backend.create_security_group(
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

    def delete(self, region_name):
        backend = rds_backends[region_name]
        backend.delete_security_group(self.group_name)


class SubnetGroup(BaseModel):
    def __init__(self, subnet_name, description, subnets):
        self.subnet_name = subnet_name
        self.description = description
        self.subnets = subnets
        self.status = "Complete"

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

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        properties = cloudformation_json["Properties"]

        subnet_name = resource_name.lower() + get_random_hex(12)
        description = properties["DBSubnetGroupDescription"]
        subnet_ids = properties["SubnetIds"]
        tags = properties.get("Tags")

        ec2_backend = ec2_backends[region_name]
        subnets = [ec2_backend.get_subnet(subnet_id) for subnet_id in subnet_ids]
        rds_backend = rds_backends[region_name]
        subnet_group = rds_backend.create_subnet_group(
            subnet_name, description, subnets, tags
        )
        return subnet_group

    def delete(self, region_name):
        backend = rds_backends[region_name]
        backend.delete_subnet_group(self.subnet_name)


class RDSBackend(BaseBackend):
    def __init__(self, region):
        self.region = region

    def __getattr__(self, attr):
        return self.rds2_backend().__getattribute__(attr)

    def reset(self):
        # preserve region
        region = self.region
        self.rds2_backend().reset()
        self.__dict__ = {}
        self.__init__(region)

    def rds2_backend(self):
        return rds2_backends[self.region]


rds_backends = dict(
    (region.name, RDSBackend(region.name)) for region in boto.rds.regions()
)
