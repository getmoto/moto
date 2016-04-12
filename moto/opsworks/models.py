from __future__ import unicode_literals
from moto.core import BaseBackend
from moto.ec2 import ec2_backends
from moto.elb import elb_backends
import uuid
import datetime

from .exceptions import ResourceNotFoundException


class Layer(object):
    def __init__(self, stack_id, type, name, shortname, attributes, 
                 custom_instance_profile_arn, custom_json, 
                 custom_security_group_ids, packages, volume_configurations,
                 enable_autohealing, auto_assign_elastic_ips, 
                 auto_assign_public_ips, custom_recipes, install_updates_on_boot,
                 use_ebs_optimized_instances, lifecycle_event_configuration):
        self.stack_id = stack_id
        self.type = type
        self.name = name
        self.shortname = shortname
        self.attributes = attributes
        self.custom_instance_profile_arn = custom_instance_profile_arn
        self.custom_json = custom_json
        self.custom_security_group_ids = custom_security_group_ids
        self.packages = packages
        self.volume_configurations = volume_configurations
        self.enable_autohealing = enable_autohealing
        self.auto_assign_elastic_ips = auto_assign_elastic_ips
        self.auto_assign_public_ips = auto_assign_public_ips
        self.custom_recipes = custom_recipes
        self.install_updates_on_boot = install_updates_on_boot
        self.use_ebs_optimized_instances = use_ebs_optimized_instances
        self.lifecycle_event_configuration = lifecycle_event_configuration
        self.instances = []


class Stack(object):
    def __init__(self, name, region, service_role_arn, default_instance_profile_arn,
                 vpcid='vpc-1f99bf7c',
                 attributes=None,
                 default_os='Ubuntu 12.04 LTS',
                 hostname_theme='Layer_Dependent',
                 default_availability_zone='us-east-1a',
                 default_subnet_id='subnet-73981004',
                 custom_json=None,
                 configuration_manager=None,
                 chef_configuration=None,
                 use_custom_cookbooks=False,
                 use_opsworks_security_groups=True,
                 custom_cookbooks_source=None,
                 default_ssh_keyname=None,
                 default_root_device_type='instance-store',
                 agent_version='LATEST'):

        self.name = name
        self.region = region
        self.service_role_arn = service_role_arn
        self.default_instance_profile_arn = default_instance_profile_arn

        self.vpcid = vpcid
        self.attributes = attributes
        if attributes is None:
            self.attributes = {'Color': None}

        self.configuration_manager = configuration_manager
        if configuration_manager is None:
            self.configuration_manager = {'Name': 'Chef', 'Version': '11.4'}

        self.chef_configuration = chef_configuration
        if chef_configuration is None:
            self.chef_configuration = {}

        self.custom_cookbooks_source = custom_cookbooks_source
        if custom_cookbooks_source is None:
            self.custom_cookbooks_source = {}

        self.custom_json = custom_json
        self.default_ssh_keyname = default_ssh_keyname
        self.default_os = default_os
        self.hostname_theme = hostname_theme
        self.default_availability_zone = default_availability_zone
        self.default_subnet_id = default_subnet_id
        self.use_custom_cookbooks = use_custom_cookbooks
        self.use_opsworks_security_groups = use_opsworks_security_groups
        self.default_root_device_type = default_root_device_type
        self.agent_version = agent_version

        self.id = "{}".format(uuid.uuid4())
        self.layers = []
        self.apps = []
        self.account_number = "123456789012"
        self.created_at = datetime.datetime.utcnow()

    def __eq__(self, other):
        return self.id == other.id

    @property
    def arn(self):
        return "arn:aws:opsworks:{region}:{account_number}:stack/{id}".format(
            region=self.region,
            account_number=self.account_number,
            id=self.id
        )

    def to_dict(self):
        response = {
            "AgentVersion": self.agent_version,
            "Arn": self.arn,
            "Attributes": self.attributes,
            "ChefConfiguration": self.chef_configuration,
            "ConfigurationManager": self.configuration_manager,
            "CreatedAt": self.created_at.isoformat(),
            "CustomCookbooksSource": self.custom_cookbooks_source,
            "DefaultAvailabilityZone": self.default_availability_zone,
            "DefaultInstanceProfileArn": self.default_instance_profile_arn,
            "DefaultOs": self.default_os,
            "DefaultRootDeviceType": self.default_root_device_type,
            "DefaultSshKeyName": self.default_ssh_keyname,
            "DefaultSubnetId": self.default_subnet_id,
            "HostnameTheme": self.hostname_theme,
            "Name": self.name,
            "Region": self.region,
            "ServiceRoleArn": self.service_role_arn,
            "StackId": self.id,
            "UseCustomCookbooks": self.use_custom_cookbooks,
            "UseOpsworksSecurityGroups": self.use_opsworks_security_groups,
            "VpcId": self.vpcid
        }
        if self.custom_json is not None:
            response.update({"CustomJson": self.custom_json})
        if self.default_ssh_keyname is not None:
            response.update({"DefaultSshKeyName": self.default_ssh_keyname})
        return response


class OpsWorksBackend(BaseBackend):
    def __init__(self, ec2_backend, elb_backend):
        self.stacks = {}
        self.layers = {}
        self.instances = {}
        self.policies = {}
        self.ec2_backend = ec2_backend
        self.elb_backend = elb_backend

    def reset(self):
        ec2_backend = self.ec2_backend
        elb_backend = self.elb_backend
        self.__dict__ = {}
        self.__init__(ec2_backend, elb_backend)

    def create_stack(self, **kwargs):
        stack = Stack(**kwargs)
        self.stacks[stack.id] = stack
        return stack

    def describe_stacks(self, stack_ids=None):
        if stack_ids is None:
            return [stack.to_dict() for stack in self.stacks.values()]

        unknown_stacks = set(stack_ids) - set(self.stacks.keys())
        if unknown_stacks:
            raise ResourceNotFoundException(unknown_stacks)
        return [self.stacks[id].to_dict() for id in stack_ids]

opsworks_backends = {}
for region, ec2_backend in ec2_backends.items():
    opsworks_backends[region] = OpsWorksBackend(ec2_backend, elb_backends[region])
