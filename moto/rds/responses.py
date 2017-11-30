from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backends
from .models import rds_backends


class RDSResponse(BaseResponse):

    @property
    def backend(self):
        return rds_backends[self.region]

    def _get_db_kwargs(self):
        args = {
            "auto_minor_version_upgrade": self._get_param('AutoMinorVersionUpgrade'),
            "allocated_storage": self._get_int_param('AllocatedStorage'),
            "availability_zone": self._get_param("AvailabilityZone"),
            "backup_retention_period": self._get_param("BackupRetentionPeriod"),
            "db_instance_class": self._get_param('DBInstanceClass'),
            "db_instance_identifier": self._get_param('DBInstanceIdentifier'),
            "db_name": self._get_param("DBName"),
            # DBParameterGroupName
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "engine": self._get_param("Engine"),
            "engine_version": self._get_param("EngineVersion"),
            "iops": self._get_int_param("Iops"),
            "kms_key_id": self._get_param("KmsKeyId"),
            "master_password": self._get_param('MasterUserPassword'),
            "master_username": self._get_param('MasterUsername'),
            "multi_az": self._get_bool_param("MultiAZ"),
            # OptionGroupName
            "port": self._get_param('Port'),
            # PreferredBackupWindow
            # PreferredMaintenanceWindow
            "publicly_accessible": self._get_param("PubliclyAccessible"),
            "region": self.region,
            "security_groups": self._get_multi_param('DBSecurityGroups.member'),
            "storage_encrypted": self._get_param("StorageEncrypted"),
            "storage_type": self._get_param("StorageType"),
            # VpcSecurityGroupIds.member.N
            "tags": list(),
        }
        args['tags'] = self.unpack_complex_list_params(
            'Tags.Tag', ('Key', 'Value'))
        return args

    def _get_db_replica_kwargs(self):
        return {
            "auto_minor_version_upgrade": self._get_param('AutoMinorVersionUpgrade'),
            "availability_zone": self._get_param("AvailabilityZone"),
            "db_instance_class": self._get_param('DBInstanceClass'),
            "db_instance_identifier": self._get_param('DBInstanceIdentifier'),
            "db_subnet_group_name": self._get_param("DBSubnetGroupName"),
            "iops": self._get_int_param("Iops"),
            # OptionGroupName
            "port": self._get_param('Port'),
            "publicly_accessible": self._get_param("PubliclyAccessible"),
            "source_db_identifier": self._get_param('SourceDBInstanceIdentifier'),
            "storage_type": self._get_param("StorageType"),
        }

    def unpack_complex_list_params(self, label, names):
        unpacked_list = list()
        count = 1
        while self._get_param('{0}.{1}.{2}'.format(label, count, names[0])):
            param = dict()
            for i in range(len(names)):
                param[names[i]] = self._get_param(
                    '{0}.{1}.{2}'.format(label, count, names[i]))
            unpacked_list.append(param)
            count += 1
        return unpacked_list

    def create_db_instance(self):
        db_kwargs = self._get_db_kwargs()

        database = self.backend.create_database(db_kwargs)
        template = self.response_template(CREATE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def create_db_instance_read_replica(self):
        db_kwargs = self._get_db_replica_kwargs()

        database = self.backend.create_database_replica(db_kwargs)
        template = self.response_template(CREATE_DATABASE_REPLICA_TEMPLATE)
        return template.render(database=database)

    def describe_db_instances(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        all_instances = list(self.backend.describe_databases(db_instance_identifier))
        marker = self._get_param('Marker')
        all_ids = [instance.db_instance_identifier for instance in all_instances]
        if marker:
            start = all_ids.index(marker) + 1
        else:
            start = 0
        page_size = self._get_param('MaxRecords', 50)  # the default is 100, but using 50 to make testing easier
        instances_resp = all_instances[start:start + page_size]
        next_marker = None
        if len(all_instances) > start + page_size:
            next_marker = instances_resp[-1].db_instance_identifier

        template = self.response_template(DESCRIBE_DATABASES_TEMPLATE)
        return template.render(databases=instances_resp, marker=next_marker)

    def modify_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        db_kwargs = self._get_db_kwargs()
        new_db_instance_identifier = self._get_param('NewDBInstanceIdentifier')
        if new_db_instance_identifier:
            db_kwargs['new_db_instance_identifier'] = new_db_instance_identifier
        database = self.backend.modify_database(
            db_instance_identifier, db_kwargs)
        template = self.response_template(MODIFY_DATABASE_TEMPLATE)
        return template.render(database=database)

    def delete_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        database = self.backend.delete_database(db_instance_identifier)
        template = self.response_template(DELETE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def create_db_security_group(self):
        group_name = self._get_param('DBSecurityGroupName')
        description = self._get_param('DBSecurityGroupDescription')
        tags = self.unpack_complex_list_params('Tags.Tag', ('Key', 'Value'))
        security_group = self.backend.create_security_group(
            group_name, description, tags)
        template = self.response_template(CREATE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def describe_db_security_groups(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_groups = self.backend.describe_security_groups(
            security_group_name)
        template = self.response_template(DESCRIBE_SECURITY_GROUPS_TEMPLATE)
        return template.render(security_groups=security_groups)

    def delete_db_security_group(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_group = self.backend.delete_security_group(
            security_group_name)
        template = self.response_template(DELETE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def authorize_db_security_group_ingress(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        cidr_ip = self._get_param('CIDRIP')
        security_group = self.backend.authorize_security_group(
            security_group_name, cidr_ip)
        template = self.response_template(AUTHORIZE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def create_db_subnet_group(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        description = self._get_param('DBSubnetGroupDescription')
        subnet_ids = self._get_multi_param('SubnetIds.member')
        subnets = [ec2_backends[self.region].get_subnet(
            subnet_id) for subnet_id in subnet_ids]
        tags = self.unpack_complex_list_params('Tags.Tag', ('Key', 'Value'))
        subnet_group = self.backend.create_subnet_group(
            subnet_name, description, subnets, tags)
        template = self.response_template(CREATE_SUBNET_GROUP_TEMPLATE)
        return template.render(subnet_group=subnet_group)

    def describe_db_subnet_groups(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        subnet_groups = self.backend.describe_subnet_groups(subnet_name)
        template = self.response_template(DESCRIBE_SUBNET_GROUPS_TEMPLATE)
        return template.render(subnet_groups=subnet_groups)

    def delete_db_subnet_group(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        subnet_group = self.backend.delete_subnet_group(subnet_name)
        template = self.response_template(DELETE_SUBNET_GROUP_TEMPLATE)
        return template.render(subnet_group=subnet_group)


CREATE_DATABASE_TEMPLATE = """<CreateDBInstanceResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBInstanceResult>
    {{ database.to_xml() }}
  </CreateDBInstanceResult>
  <ResponseMetadata>
    <RequestId>523e3218-afc7-11c3-90f5-f90431260ab4</RequestId>
  </ResponseMetadata>
</CreateDBInstanceResponse>"""

CREATE_DATABASE_REPLICA_TEMPLATE = """<CreateDBInstanceReadReplicaResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBInstanceReadReplicaResult>
    {{ database.to_xml() }}
  </CreateDBInstanceReadReplicaResult>
  <ResponseMetadata>
    <RequestId>ba8dedf0-bb9a-11d3-855b-576787000e19</RequestId>
  </ResponseMetadata>
</CreateDBInstanceReadReplicaResponse>"""

DESCRIBE_DATABASES_TEMPLATE = """<DescribeDBInstancesResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBInstancesResult>
    <DBInstances>
    {% for database in databases %}
        {{ database.to_xml() }}
    {% endfor %}
    </DBInstances>
    {% if marker %}
    <Marker>{{ marker }}</Marker>
    {% endif %}
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

CREATE_SUBNET_GROUP_TEMPLATE = """<CreateDBSubnetGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <CreateDBSubnetGroupResult>
    {{ subnet_group.to_xml() }}
  </CreateDBSubnetGroupResult>
  <ResponseMetadata>
    <RequestId>3a401b3f-bb9e-11d3-f4c6-37db295f7674</RequestId>
  </ResponseMetadata>
</CreateDBSubnetGroupResponse>"""

DESCRIBE_SUBNET_GROUPS_TEMPLATE = """<DescribeDBSubnetGroupsResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <DescribeDBSubnetGroupsResult>
    <DBSubnetGroups>
    {% for subnet_group in subnet_groups %}
        {{ subnet_group.to_xml() }}
    {% endfor %}
    </DBSubnetGroups>
  </DescribeDBSubnetGroupsResult>
  <ResponseMetadata>
    <RequestId>b783db3b-b98c-11d3-fbc7-5c0aad74da7c</RequestId>
  </ResponseMetadata>
</DescribeDBSubnetGroupsResponse>"""

DELETE_SUBNET_GROUP_TEMPLATE = """<DeleteDBSubnetGroupResponse xmlns="http://rds.amazonaws.com/doc/2014-09-01/">
  <ResponseMetadata>
    <RequestId>6295e5ab-bbf3-11d3-f4c6-37db295f7674</RequestId>
  </ResponseMetadata>
</DeleteDBSubnetGroupResponse>"""
