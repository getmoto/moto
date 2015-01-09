from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from .models import rds_backends


class RDSResponse(BaseResponse):

    @property
    def backend(self):
        return rds_backends[self.region]

    def create_dbinstance(self):
        db_kwargs = {
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
            # DBSecurityGroups.member.N
            # VpcSecurityGroupIds.member.N

            "availability_zone": self._get_param("AvailabilityZone"),
            "multi_az": self._get_bool_param("MultiAZ"),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
        }

        database = self.backend.create_database(db_kwargs)
        template = self.response_template(CREATE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def describe_dbinstances(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        databases = self.backend.describe_databases(db_instance_identifier)
        template = self.response_template(DESCRIBE_DATABASES_TEMPLATE)
        return template.render(databases=databases)

    def delete_dbinstance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        database = self.backend.delete_database(db_instance_identifier)
        template = self.response_template(DELETE_DATABASE_TEMPLATE)
        return template.render(database=database)


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

DELETE_DATABASE_TEMPLATE = """<DeleteDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DeleteDBInstanceResult>
    {{ database.to_xml() }}
  </DeleteDBInstanceResult>
  <ResponseMetadata>
    <RequestId>7369556f-b70d-11c3-faca-6ba18376ea1b</RequestId>
  </ResponseMetadata>
</DeleteDBInstanceResponse>"""
