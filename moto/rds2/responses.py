from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backends
from .models import rds2_backends
import json


class RDS2Response(BaseResponse):

    @property
    def backend(self):
        return rds2_backends[self.region]

    def _get_db_kwargs(self):
        return {
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
            "storage_type": self._get_param("StorageType"),
            # VpcSecurityGroupIds.member.N
        }

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

    def _get_option_group_kwargs(self):
        return {
            'major_engine_version': self._get_param('MajorEngineVersion'),
            'description': self._get_param('OptionGroupDescription'),
            'engine_name': self._get_param('EngineName'),
            'name': self._get_param('OptionGroupName')
        }

    def create_dbinstance(self):
        return self.create_db_instance()

    def create_db_instance(self):
        db_kwargs = self._get_db_kwargs()
        database = self.backend.create_database(db_kwargs)
        template = self.response_template(CREATE_DATABASE_TEMPLATE)
        result = template.render(database=database)
        return result

    # TODO: Update function to new method
    def create_dbinstance_read_replica(self):
        db_kwargs = self._get_db_replica_kwargs()

        database = self.backend.create_database_replica(db_kwargs)
        template = self.response_template(CREATE_DATABASE_REPLICA_TEMPLATE)
        return template.render(database=database)

    def describe_dbinstances(self):
        return self.describe_db_instances()

    def describe_dbinstances(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        databases = self.backend.describe_databases(db_instance_identifier)
        template = self.response_template(DESCRIBE_DATABASES_TEMPLATE)
        return template.render(databases=databases)

    def modify_dbinstance(self):
        return self.modify_db_instance()

    def modify_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        db_kwargs = self._get_db_kwargs()
        database = self.backend.modify_database(db_instance_identifier, db_kwargs)
        template = self.response_template(MODIFY_DATABASE_TEMPLATE)
        return template.render(database=database)

    def delete_dbinstance(self):
        return self.delete_db_instance()

    def delete_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        database = self.backend.delete_database(db_instance_identifier)
        template = self.response_template(DELETE_DATABASE_TEMPLATE)
        return template.render(database=database)

    # TODO: Update function to new method
    def create_dbsecurity_group(self):
        group_name = self._get_param('DBSecurityGroupName')
        description = self._get_param('DBSecurityGroupDescription')
        security_group = self.backend.create_security_group(group_name, description)
        template = self.response_template(CREATE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    # TODO: Update function to new method
    def describe_dbsecurity_groups(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_groups = self.backend.describe_security_groups(security_group_name)
        template = self.response_template(DESCRIBE_SECURITY_GROUPS_TEMPLATE)
        return template.render(security_groups=security_groups)

    # TODO: Update function to new method
    def delete_dbsecurity_group(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_group = self.backend.delete_security_group(security_group_name)
        template = self.response_template(DELETE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    # TODO: Update function to new method
    def authorize_dbsecurity_group_ingress(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        cidr_ip = self._get_param('CIDRIP')
        security_group = self.backend.authorize_security_group(security_group_name, cidr_ip)
        template = self.response_template(AUTHORIZE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    # TODO: Update function to new method
    def create_dbsubnet_group(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        description = self._get_param('DBSubnetGroupDescription')
        subnet_ids = self._get_multi_param('SubnetIds.member')
        subnets = [ec2_backends[self.region].get_subnet(subnet_id) for subnet_id in subnet_ids]
        subnet_group = self.backend.create_subnet_group(subnet_name, description, subnets)
        template = self.response_template(CREATE_SUBNET_GROUP_TEMPLATE)
        return template.render(subnet_group=subnet_group)

    # TODO: Update function to new method
    def describe_dbsubnet_groups(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        subnet_groups = self.backend.describe_subnet_groups(subnet_name)
        template = self.response_template(DESCRIBE_SUBNET_GROUPS_TEMPLATE)
        return template.render(subnet_groups=subnet_groups)

    # TODO: Update function to new method
    def delete_dbsubnet_group(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        subnet_group = self.backend.delete_subnet_group(subnet_name)
        template = self.response_template(DELETE_SUBNET_GROUP_TEMPLATE)
        return template.render(subnet_group=subnet_group)

    def create_option_group(self):
        kwargs = self._get_option_group_kwargs()
        option_group = self.backend.create_option_group(kwargs)
        template = self.response_template(CREATE_OPTION_GROUP_TEMPLATE)
        return template.render(option_group=option_group)

    def delete_option_group(self):
        kwargs = self._get_option_group_kwargs()
        option_group = self.backend.delete_option_group(kwargs['name'])
        template = self.response_template(DELETE_OPTION_GROUP_TEMPLATE)
        return template.render(option_group=option_group)

    def describe_option_groups(self):
        kwargs = self._get_option_group_kwargs()
        kwargs['max_records'] = self._get_param('MaxRecords')
        kwargs['marker'] = self._get_param('Marker')
        option_groups = self.backend.describe_option_groups(kwargs)
        template = self.response_template(DESCRIBE_OPTION_GROUP_TEMPLATE)
        return template.render(option_groups=option_groups)

    def describe_option_group_options(self):
        engine_name = self._get_param('EngineName')
        major_engine_version = self._get_param('MajorEngineVersion')
        option_group_options = self.backend.describe_option_group_options(engine_name, major_engine_version)
        return option_group_options

    def modify_option_group(self):
        option_group_name = self._get_param('OptionGroupName')
        count = 1
        options_to_include = []
        while self._get_param('OptionsToInclude.member.{}.OptionName'.format(count)):
            options_to_include.append({
                'Port': self._get_param('OptionsToInclude.member.{}.Port'.format(count)),
                'OptionName': self._get_param('OptionsToInclude.member.{}.OptionName'.format(count)),
                'DBSecurityGroupMemberships': self._get_param('OptionsToInclude.member.{}.DBSecurityGroupMemberships'.format(count)),
                'OptionSettings': self._get_param('OptionsToInclude.member.{}.OptionSettings'.format(count)),
                'VpcSecurityGroupMemberships': self._get_param('OptionsToInclude.member.{}.VpcSecurityGroupMemberships'.format(count))
            })
            count += 1

        count = 1
        options_to_remove = []
        while self._get_param('OptionsToRemove.member.{}'.format(count)):
            options_to_remove.append(self._get_param('OptionsToRemove.member.{}'.format(count)))
            count += 1
        apply_immediately = self._get_param('ApplyImmediately')
        option_group = self.backend.modify_option_group(option_group_name,
                                                        options_to_include,
                                                        options_to_remove,
                                                        apply_immediately)
        template = self.response_template(MODIFY_OPTION_GROUP_TEMPLATE)
        return template.render(option_group=option_group)


CREATE_DATABASE_TEMPLATE = """{
  "CreateDBInstanceResponse": {
    "CreateDBInstanceResult": {
      {{ database.to_json() }}
    },
    "ResponseMetadata": { "RequestId": "523e3218-afc7-11c3-90f5-f90431260ab4" }
  }
}"""

CREATE_DATABASE_REPLICA_TEMPLATE = """{
  "CreateDBInstanceResponse": {
    "CreateDBInstanceResult": {
      {{ database.to_json() }}
    },
    "ResponseMetadata": { "RequestId": "523e3218-afc7-11c3-90f5-f90431260ab4" }
  }
}"""

DESCRIBE_DATABASES_TEMPLATE = """{
  "DescribeDBInstanceResponse": {
    "DescribeDBInstanceResult": [
      {%- for database in databases -%}
        {%- if loop.index != 1 -%},{%- endif -%}
        { {{ database.to_json() }} }
      {%- endfor -%}
    ],
    "ResponseMetadata": { "RequestId": "523e3218-afc7-11c3-90f5-f90431260ab4" }
  }
}"""

MODIFY_DATABASE_TEMPLATE = """{"ModifyDBInstanceResponse": {
    "ModifyDBInstanceResult": {
      {{ database.to_json() }},
      "ResponseMetadata": {
        "RequestId": "bb58476c-a1a8-11e4-99cf-55e92d4bbada"
      }
    }
  }
}"""

# TODO: update delete DB TEMPLATE
DELETE_DATABASE_TEMPLATE = """{
  "DeleteDBInstanceResponse": {
    "DeleteDBInstanceResult": {
    },
    "ResponseMetadata": { "RequestId": "523e3218-afc7-11c3-90f5-f90431260ab4" }
  }
}"""

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

CREATE_SUBNET_GROUP_TEMPLATE = """{
  "CreateDBSubnetGroupResponse": {
    "CreateDBSubnetGroupResult":
        {{ subnet_group.to_json() }},
    "ResponseMetadata": { "RequestId": "3a401b3f-bb9e-11d3-f4c6-37db295f7674" }
  }
}"""

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

CREATE_OPTION_GROUP_TEMPLATE = """{
    "CreateOptionGroupResponse": {
        "CreateOptionGroupResult": {
            "OptionGroup": {{ option_group.to_json() }}
        },
        "ResponseMetadata": {
            "RequestId": "1e38dad4-9f50-11e4-87ea-a31c60ed2e36"
        }
    }
}"""

DELETE_OPTION_GROUP_TEMPLATE = \
    """{"DeleteOptionGroupResponse": {"ResponseMetadata": {"RequestId": "e2590367-9fa2-11e4-99cf-55e92d41c60e"}}}"""

DESCRIBE_OPTION_GROUP_TEMPLATE = \
    """{"DescribeOptionGroupsResponse": {
          "DescribeOptionGroupsResult": {
            "Marker": null,
            "OptionGroupsList": [
            {%- for option_group in option_groups -%}
                {%- if loop.index != 1 -%},{%- endif -%}
                {{ option_group.to_json() }}
            {%- endfor -%}
            ]},
            "ResponseMetadata": {"RequestId": "4caf445d-9fbc-11e4-87ea-a31c60ed2e36"}
        }}"""

DESCRIBE_OPTION_GROUP_OPTIONS_TEMPLATE = \
    """{"DescribeOptionGroupOptionsResponse": {
          "DescribeOptionGroupOptionsResult": {
            "Marker": null,
            "OptionGroupOptions": [
                {%- for option_group_option in option_group_options -%}
                {%- if loop.index != 1 -%},{%- endif -%}
                {{ option_group_option.to_json() }}
                {%- endfor -%}
            ]},
          "ResponseMetadata": {"RequestId": "457f7bb8-9fbf-11e4-9084-5754f80d5144"}
        }}"""

MODIFY_OPTION_GROUP_TEMPLATE = \
    """{"ModifyOptionGroupResponse": {
          "ResponseMetadata": {
              "RequestId": "ce9284a5-a0de-11e4-b984-a11a53e1f328"
          },
          "ModifyOptionGroupResult":
            {{ option_group.to_json() }}
        }
      }"""
