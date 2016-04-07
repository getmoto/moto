from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backends
from .models import rds2_backends
import json
import re


class RDS2Response(BaseResponse):

    @property
    def backend(self):
        return rds2_backends[self.region]

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
            "master_user_password": self._get_param('MasterUserPassword'),
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
            "tags": list()
        }
        args['tags'] = self.unpack_complex_list_params('Tags.member', ('Key', 'Value'))
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

    def _get_option_group_kwargs(self):
        return {
            'major_engine_version': self._get_param('MajorEngineVersion'),
            'description': self._get_param('OptionGroupDescription'),
            'engine_name': self._get_param('EngineName'),
            'name': self._get_param('OptionGroupName')
        }

    def unpack_complex_list_params(self, label, names):
        unpacked_list = list()
        count = 1
        while self._get_param('{0}.{1}.{2}'.format(label, count, names[0])):
            param = dict()
            for i in range(len(names)):
                param[names[i]] = self._get_param('{0}.{1}.{2}'.format(label, count, names[i]))
            unpacked_list.append(param)
            count += 1
        return unpacked_list

    def unpack_list_params(self, label):
        unpacked_list = list()
        count = 1
        while self._get_param('{0}.{1}'.format(label, count)):
            unpacked_list.append(self._get_param('{0}.{1}'.format(label, count)))
            count += 1
        return unpacked_list

    def create_dbinstance(self):
        return self.create_db_instance()

    def create_db_instance(self):
        db_kwargs = self._get_db_kwargs()
        database = self.backend.create_database(db_kwargs)
        template = self.response_template(CREATE_DATABASE_TEMPLATE)
        return template.render(database=database)

    def create_dbinstance_read_replica(self):
        return self.create_db_instance_read_replica()

    def create_db_instance_read_replica(self):
        db_kwargs = self._get_db_replica_kwargs()

        database = self.backend.create_database_replica(db_kwargs)
        template = self.response_template(CREATE_DATABASE_REPLICA_TEMPLATE)
        return template.render(database=database)

    def describe_dbinstances(self):
        return self.describe_db_instances()

    def describe_db_instances(self):
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

    def reboot_dbinstance(self):
        return self.reboot_db_instance()

    def reboot_db_instance(self):
        db_instance_identifier = self._get_param('DBInstanceIdentifier')
        database = self.backend.reboot_db_instance(db_instance_identifier)
        template = self.response_template(REBOOT_DATABASE_TEMPLATE)
        return template.render(database=database)

    def list_tags_for_resource(self):
        arn = self._get_param('ResourceName')
        template = self.response_template(LIST_TAGS_FOR_RESOURCE_TEMPLATE)
        tags = self.backend.list_tags_for_resource(arn)
        return template.render(tags=tags)

    def add_tags_to_resource(self):
        arn = self._get_param('ResourceName')
        tags = self.unpack_complex_list_params('Tags.member', ('Key', 'Value'))
        tags = self.backend.add_tags_to_resource(arn, tags)
        template = self.response_template(ADD_TAGS_TO_RESOURCE_TEMPLATE)
        return template.render(tags=tags)

    def remove_tags_from_resource(self):
        arn = self._get_param('ResourceName')
        tag_keys = self.unpack_list_params('TagKeys.member')
        self.backend.remove_tags_from_resource(arn, tag_keys)
        template = self.response_template(REMOVE_TAGS_FROM_RESOURCE_TEMPLATE)
        return template.render()

    def create_dbsecurity_group(self):
        return self.create_db_security_group()

    def create_db_security_group(self):
        group_name = self._get_param('DBSecurityGroupName')
        description = self._get_param('DBSecurityGroupDescription')
        security_group = self.backend.create_security_group(group_name, description)
        template = self.response_template(CREATE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def describe_dbsecurity_groups(self):
        return self.describe_db_security_groups()

    def describe_db_security_groups(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_groups = self.backend.describe_security_groups(security_group_name)
        template = self.response_template(DESCRIBE_SECURITY_GROUPS_TEMPLATE)
        return template.render(security_groups=security_groups)

    def delete_dbsecurity_group(self):
        return self.delete_db_security_group()

    def delete_db_security_group(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        security_group = self.backend.delete_security_group(security_group_name)
        template = self.response_template(DELETE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def authorize_dbsecurity_group_ingress(self):
        return self.authorize_db_security_group_ingress()

    def authorize_db_security_group_ingress(self):
        security_group_name = self._get_param('DBSecurityGroupName')
        cidr_ip = self._get_param('CIDRIP')
        security_group = self.backend.authorize_security_group(security_group_name, cidr_ip)
        template = self.response_template(AUTHORIZE_SECURITY_GROUP_TEMPLATE)
        return template.render(security_group=security_group)

    def create_dbsubnet_group(self):
        return self.create_db_subnet_group()

    def create_db_subnet_group(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        description = self._get_param('DBSubnetGroupDescription')
        subnet_ids = self._get_multi_param('SubnetIds.member')
        subnets = [ec2_backends[self.region].get_subnet(subnet_id) for subnet_id in subnet_ids]
        subnet_group = self.backend.create_subnet_group(subnet_name, description, subnets)
        template = self.response_template(CREATE_SUBNET_GROUP_TEMPLATE)
        return template.render(subnet_group=subnet_group)

    def describe_dbsubnet_groups(self):
        return self.describe_db_subnet_groups()

    def describe_db_subnet_groups(self):
        subnet_name = self._get_param('DBSubnetGroupName')
        subnet_groups = self.backend.describe_subnet_groups(subnet_name)
        template = self.response_template(DESCRIBE_SUBNET_GROUPS_TEMPLATE)
        return template.render(subnet_groups=subnet_groups)

    def delete_dbsubnet_group(self):
        return self.delete_db_subnet_group()

    def delete_db_subnet_group(self):
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
        while self._get_param('OptionsToInclude.member.{0}.OptionName'.format(count)):
            options_to_include.append({
                'Port': self._get_param('OptionsToInclude.member.{0}.Port'.format(count)),
                'OptionName': self._get_param('OptionsToInclude.member.{0}.OptionName'.format(count)),
                'DBSecurityGroupMemberships': self._get_param('OptionsToInclude.member.{0}.DBSecurityGroupMemberships'.format(count)),
                'OptionSettings': self._get_param('OptionsToInclude.member.{0}.OptionSettings'.format(count)),
                'VpcSecurityGroupMemberships': self._get_param('OptionsToInclude.member.{0}.VpcSecurityGroupMemberships'.format(count))
            })
            count += 1

        count = 1
        options_to_remove = []
        while self._get_param('OptionsToRemove.member.{0}'.format(count)):
            options_to_remove.append(self._get_param('OptionsToRemove.member.{0}'.format(count)))
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
      "DBInstance": {{ database.to_json() }}
    },
    "ResponseMetadata": { "RequestId": "523e3218-afc7-11c3-90f5-f90431260ab4" }
  }
}"""

CREATE_DATABASE_REPLICA_TEMPLATE = """{"CreateDBInstanceReadReplicaResponse": {
  "ResponseMetadata": {
    "RequestId": "5e60c46d-a844-11e4-bb68-17f36418e58f"
  },
  "CreateDBInstanceReadReplicaResult": {
    "DBInstance": {{ database.to_json() }}
  }
}}"""

DESCRIBE_DATABASES_TEMPLATE = """{
  "DescribeDBInstancesResponse": {
    "DescribeDBInstancesResult": {
      "DBInstances": [
        {%- for database in databases -%}
          {%- if loop.index != 1 -%},{%- endif -%}
          {{ database.to_json() }}
        {%- endfor -%}
      ]
    },
    "ResponseMetadata": { "RequestId": "523e3218-afc7-11c3-90f5-f90431260ab4" }
  }
}"""

MODIFY_DATABASE_TEMPLATE = """{"ModifyDBInstanceResponse": {
    "ModifyDBInstanceResult": {
      "DBInstance": {{ database.to_json() }},
      "ResponseMetadata": {
        "RequestId": "bb58476c-a1a8-11e4-99cf-55e92d4bbada"
      }
    }
  }
}"""

REBOOT_DATABASE_TEMPLATE = """{"RebootDBInstanceResponse": {
    "RebootDBInstanceResult": {
      "DBInstance": {{ database.to_json() }},
      "ResponseMetadata": {
        "RequestId": "d55711cb-a1ab-11e4-99cf-55e92d4bbada"
      }
    }
  }
}"""


DELETE_DATABASE_TEMPLATE = """{ "DeleteDBInstanceResponse": {
    "DeleteDBInstanceResult": {
      "DBInstance": {{ database.to_json() }}
    },
    "ResponseMetadata": {
      "RequestId": "523e3218-afc7-11c3-90f5-f90431260ab4"
    }
  }
}"""

CREATE_SECURITY_GROUP_TEMPLATE = """{"CreateDBSecurityGroupResponse": {
    "CreateDBSecurityGroupResult": {
        "DBSecurityGroup":
            {{ security_group.to_json() }},
        "ResponseMetadata": {
            "RequestId": "462165d0-a77a-11e4-a5fa-75b30c556f97"
        }}
    }
}"""

DESCRIBE_SECURITY_GROUPS_TEMPLATE = """{
    "DescribeDBSecurityGroupsResponse": {
        "ResponseMetadata": {
            "RequestId": "5df2014e-a779-11e4-bdb0-594def064d0c"
        },
        "DescribeDBSecurityGroupsResult": {
            "Marker": "null",
            "DBSecurityGroups": [
            {% for security_group in security_groups %}
                {%- if loop.index != 1 -%},{%- endif -%}
                {{ security_group.to_json() }}
            {% endfor %}
            ]
        }
    }
}"""

DELETE_SECURITY_GROUP_TEMPLATE = """{"DeleteDBSecurityGroupResponse": {
  "ResponseMetadata": {
    "RequestId": "97e846bd-a77d-11e4-ac58-91351c0f3426"
  }
}}"""

AUTHORIZE_SECURITY_GROUP_TEMPLATE = """{
    "AuthorizeDBSecurityGroupIngressResponse": {
        "AuthorizeDBSecurityGroupIngressResult": {
            "DBSecurityGroup": {{ security_group.to_json() }}
        },
        "ResponseMetadata": {
            "RequestId": "75d32fd5-a77e-11e4-8892-b10432f7a87d"
        }
    }
}"""

CREATE_SUBNET_GROUP_TEMPLATE = """{
  "CreateDBSubnetGroupResponse": {
    "CreateDBSubnetGroupResult":
        { {{ subnet_group.to_json() }} },
    "ResponseMetadata": { "RequestId": "3a401b3f-bb9e-11d3-f4c6-37db295f7674" }
  }
}"""

DESCRIBE_SUBNET_GROUPS_TEMPLATE = """{
  "DescribeDBSubnetGroupsResponse": {
    "DescribeDBSubnetGroupsResult": {
      "DBSubnetGroups": [
              {% for subnet_group in subnet_groups %}
                  { {{ subnet_group.to_json() }} }{%- if not loop.last -%},{%- endif -%}
              {% endfor %}
          ],
          "Marker": null
    },
    "ResponseMetadata": { "RequestId": "b783db3b-b98c-11d3-fbc7-5c0aad74da7c" }
  }
}"""


DELETE_SUBNET_GROUP_TEMPLATE = """{"DeleteDBSubnetGroupResponse": {"ResponseMetadata": {"RequestId": "13785dd5-a7fc-11e4-bb9c-7f371d0859b0"}}}"""

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

LIST_TAGS_FOR_RESOURCE_TEMPLATE = \
    """{"ListTagsForResourceResponse":
      {"ListTagsForResourceResult":
        {"TagList": [
          {%- for tag in tags -%}
            {%- if loop.index != 1 -%},{%- endif -%}
            {
              "Key": "{{ tag['Key'] }}",
              "Value": "{{ tag['Value'] }}"
            }
          {%- endfor -%}
        ]},
        "ResponseMetadata": {
          "RequestId": "8c21ba39-a598-11e4-b688-194eaf8658fa"
        }
      }
    }"""

ADD_TAGS_TO_RESOURCE_TEMPLATE = \
   """{"ListTagsForResourceResponse":  {
         "ListTagsForResourceResult": {
           "TagList": [
           {%- for tag in tags -%}
               {%- if loop.index != 1 -%},{%- endif -%}
               {
                  "Key": "{{ tag['Key'] }}",
                  "Value": "{{ tag['Value'] }}"
               }
           {%- endfor -%}
           ]},
           "ResponseMetadata": {
             "RequestId": "b194d9ca-a664-11e4-b688-194eaf8658fa"
           }
         }
   }"""

REMOVE_TAGS_FROM_RESOURCE_TEMPLATE = \
   """{"RemoveTagsFromResourceResponse": {"ResponseMetadata": {"RequestId": "c6499a01-a664-11e4-8069-fb454b71a80e"}}}
   """
