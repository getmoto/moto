from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from .models import rds_backends


class RDSResponse(BaseResponse):

    @property
    def backend(self):
        return rds_backends[self.region]

    def _get_db_kwargs(self):
        return {
            "engine": self._get_param("Engine"),
            "engine_version": self._get_param("EngineVersion"),
            "region": self.region,
            "iops": self._get_int_param("Iops"),
            "storage_type": self._get_param("StorageType"),

            "master_username": self._get_param('MasterUsername'),
            "master_password": self._get_param('MasterUserPassword'),
            "auto_minor_version_upgrade": self._get_param('AutoMinorVersionUpgrade'),
            "allocated_storage": self._get_int_param('AllocatedStorage'),
            "db_instance_class": self._get_param('DBInstanceClass'),
            "port": self._get_param('Port'),
            "db_instance_identifier": self._get_param('DBInstanceIdentifier'),
            "db_name": self._get_param("DBName"),
            "publicly_accessible": self._get_param("PubliclyAccessible"),

            # PreferredBackupWindow
            # PreferredMaintenanceWindow
            "backup_retention_period": self._get_param("BackupRetentionPeriod"),

            # OptionGroupName
            # DBParameterGroupName
            "security_groups": self._get_multi_param('DBSecurityGroups.member'),
            # VpcSecurityGroupIds.member.N

            "availability_zone": self._get_param("AvailabilityZone"),
            "multi_az": self._get_bool_param("MultiAZ"),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
        }

    def create_dbinstance(self):
        db_kwargs = self._get_db_kwargs()

        database = self.backend.create_database(db_kwargs)
        template = self.response_template(CREATE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def describe_dbinstances(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        databases = self.backend.describe_databases(db_instance_identifier)
        template = self.response_template(DESCRIBE_DATABASES_TEMPLATE)
        return template.render(databases=databases)

    def modify_dbinstance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        db_kwargs = self._get_db_kwargs()
        database = self.backend.modify_database(db_instance_identifier, db_kwargs)
        template = self.response_template(MODIFY_DATABASE_TEMPLATE)
        return template.render(database=database)

    def delete_dbinstance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        database = self.backend.delete_database(db_instance_identifier)
        template = self.response_template(DELETE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def create_dbsecurity_group(self):
        group_name = self._get_param('DBSecurityGroupName')
        description = self._get_param('DBSecurityGroupDescription')
        security_group = self.backend.create_security_group(group_name, description)
        template = self.response_template(CREATE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def describe_dbsecurity_groups(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_groups = self.backend.describe_security_groups(security_group_name)
        template = self.response_template(DESCRIBE_SECURITY_GROUPS_TEMPLATE)
        return template.render(security_groups=security_groups)

    def delete_dbsecurity_group(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_group = self.backend.delete_security_group(security_group_name)
        template = self.response_template(DELETE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def authorize_dbsecurity_group_ingress(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        cidr_ip = self._get_param('CIDRIP')
        security_group = self.backend.authorize_security_group(security_group_name, cidr_ip)
        template = self.response_template(AUTHORIZE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)


CREATE_DATABASE_TEMPLATE = """<CreateDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBInstanceResult>
    {{ database.to_xml() }}
  </CreateDBInstanceResult>
  <ResponseMetadata>
    <RequestId>523e3218-afc7-11c3-90f5-f90431260ab4</RequestId>
  </ResponseMetadata>
</CreateDBInstanceResponse>"""

DESCRIBE_DATABASES_TEMPLATE = """<DescribeDBInstancesResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBInstancesResult>
    <DBInstances>
    {% for database in databases %}
        {{ database.to_xml() }}
    {% endfor %}
    </DBInstances>
  </DescribeDBInstancesResult>
  <ResponseMetadata>
    <RequestId>01b2685a-b978-11d3-f272-7cd6cce12cc5</RequestId>
  </ResponseMetadata>
</DescribeDBInstancesResponse>"""

MODIFY_DATABASE_TEMPLATE = """<ModifyDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ModifyDBInstanceResult>
    {{ database.to_xml() }}
  </ModifyDBInstanceResult>
  <ResponseMetadata>
    <RequestId>f643f1ac-bbfe-11d3-f4c6-37db295f7674</RequestId>
  </ResponseMetadata>
</ModifyDBInstanceResponse>"""

DELETE_DATABASE_TEMPLATE = """<DeleteDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DeleteDBInstanceResult>
    {{ database.to_xml() }}
  </DeleteDBInstanceResult>
  <ResponseMetadata>
    <RequestId>7369556f-b70d-11c3-faca-6ba18376ea1b</RequestId>
  </ResponseMetadata>
</DeleteDBInstanceResponse>"""

CREATE_SECURITY_GROUP_TEMPLATE = """<CreateDBSecurityGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBSecurityGroupResult>
    {{ security_group.to_xml() }}
  </CreateDBSecurityGroupResult>
  <ResponseMetadata>
    <RequestId>e68ef6fa-afc1-11c3-845a-476777009d19</RequestId>
  </ResponseMetadata>
</CreateDBSecurityGroupResponse>"""

DESCRIBE_SECURITY_GROUPS_TEMPLATE = """<DescribeDBSecurityGroupsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBSecurityGroupsResult>
    <DBSecurityGroups>
    {% for security_group in security_groups %}
        {{ security_group.to_xml() }}
    {% endfor %}
    </DBSecurityGroups>
  </DescribeDBSecurityGroupsResult>
  <ResponseMetadata>
    <RequestId>b76e692c-b98c-11d3-a907-5a2c468b9cb0</RequestId>
  </ResponseMetadata>
</DescribeDBSecurityGroupsResponse>"""

DELETE_SECURITY_GROUP_TEMPLATE = """<DeleteDBSecurityGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ResponseMetadata>
    <RequestId>7aec7454-ba25-11d3-855b-576787000e19</RequestId>
  </ResponseMetadata>
</DeleteDBSecurityGroupResponse>"""

AUTHORIZE_SECURITY_GROUP_TEMPLATE = """<AuthorizeDBSecurityGroupIngressResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <AuthorizeDBSecurityGroupIngressResult>
  {{ security_group.to_xml() }}
  </AuthorizeDBSecurityGroupIngressResult>
  <ResponseMetadata>
    <RequestId>6176b5f8-bfed-11d3-f92b-31fa5e8dbc99</RequestId>
  </ResponseMetadata>
</AuthorizeDBSecurityGroupIngressResponse>"""
