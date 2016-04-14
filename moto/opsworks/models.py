from __future__ import unicode_literals
from moto.core import BaseBackend
from moto.ec2 import ec2_backends
from moto.elb import elb_backends
import uuid
import datetime

from .exceptions import ResourceNotFoundException, ValidationException


class Layer(object):
    def __init__(self, stack_id, type, name, shortname,
                 attributes=None,
                 custom_instance_profile_arn=None,
                 custom_json=None,
                 custom_security_group_ids=None,
                 packages=None,
                 volume_configurations=None,
                 enable_autohealing=None,
                 auto_assign_elastic_ips=None,
                 auto_assign_public_ips=None,
                 custom_recipes=None,
                 install_updates_on_boot=None,
                 use_ebs_optimized_instances=None,
                 lifecycle_event_configuration=None):
        self.stack_id = stack_id
        self.type = type
        self.name = name
        self.shortname = shortname

        self.attributes = attributes
        if attributes is None:
            self.attributes = {
                'BundlerVersion': None,
                'EcsClusterArn': None,
                'EnableHaproxyStats': None,
                'GangliaPassword': None,
                'GangliaUrl': None,
                'GangliaUser': None,
                'HaproxyHealthCheckMethod': None,
                'HaproxyHealthCheckUrl': None,
                'HaproxyStatsPassword': None,
                'HaproxyStatsUrl': None,
                'HaproxyStatsUser': None,
                'JavaAppServer': None,
                'JavaAppServerVersion': None,
                'Jvm': None,
                'JvmOptions': None,
                'JvmVersion': None,
                'ManageBundler': None,
                'MemcachedMemory': None,
                'MysqlRootPassword': None,
                'MysqlRootPasswordUbiquitous': None,
                'NodejsVersion': None,
                'PassengerVersion': None,
                'RailsStack': None,
                'RubyVersion': None,
                'RubygemsVersion': None
            }  # May not be accurate

        self.packages = packages
        if packages is None:
            self.packages = packages

        self.custom_recipes = custom_recipes
        if custom_recipes is None:
            self.custom_recipes = {
                'Configure': [],
                'Deploy': [],
                'Setup': [],
                'Shutdown': [],
                'Undeploy': [],
            }

        self.custom_security_group_ids = custom_security_group_ids
        if custom_security_group_ids is None:
            self.custom_security_group_ids = []

        self.lifecycle_event_configuration = lifecycle_event_configuration
        if lifecycle_event_configuration is None:
            self.lifecycle_event_configuration = {
                "Shutdown": {"DelayUntilElbConnectionsDrained": False}
            }

        self.volume_configurations = volume_configurations
        if volume_configurations is None:
            self.volume_configurations = []

        self.custom_instance_profile_arn = custom_instance_profile_arn
        self.custom_json = custom_json
        self.enable_autohealing = enable_autohealing
        self.auto_assign_elastic_ips = auto_assign_elastic_ips
        self.auto_assign_public_ips = auto_assign_public_ips
        self.install_updates_on_boot = install_updates_on_boot
        self.use_ebs_optimized_instances = use_ebs_optimized_instances

        self.instances = []
        self.id = "{}".format(uuid.uuid4())
        self.created_at = datetime.datetime.utcnow()

    def __eq__(self, other):
        return self.id == other.id

    def to_dict(self):
        d = {
            "Attributes": self.attributes,
            "AutoAssignElasticIps": self.auto_assign_elastic_ips,
            "AutoAssignPublicIps": self.auto_assign_public_ips,
            "CreatedAt": self.created_at.isoformat(),
            "CustomRecipes": self.custom_recipes,
            "CustomSecurityGroupIds": self.custom_security_group_ids,
            "DefaultRecipes": {
                "Configure": [],
                "Setup": [],
                "Shutdown": [],
                "Undeploy": []
            },  # May not be accurate
            "DefaultSecurityGroupNames": ['AWS-OpsWorks-Custom-Server'],
            "EnableAutoHealing": self.enable_autohealing,
            "LayerId": self.id,
            "LifecycleEventConfiguration": self.lifecycle_event_configuration,
            "Name": self.name,
            "Shortname": self.shortname,
            "StackId": self.stack_id,
            "Type": self.type,
            "UseEbsOptimizedInstances": self.use_ebs_optimized_instances,
            "VolumeConfigurations": self.volume_configurations,
        }
        if self.custom_json is not None:
            d.update({"CustomJson": self.custom_json})
        if self.custom_instance_profile_arn is not None:
            d.update({"CustomInstanceProfileArn": self.custom_instance_profile_arn})
        return d


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

    def create_layer(self, **kwargs):
        name = kwargs['name']
        shortname = kwargs['shortname']
        stackid = kwargs['stack_id']
        if stackid not in self.stacks:
            raise ResourceNotFoundException(stackid)
        if name in [l.name for l in self.layers.values()]:
            raise ValidationException(
                'There is already a layer named "{}" '
                'for this stack'.format(name))
        if shortname in [l.shortname for l in self.layers.values()]:
            raise ValidationException(
                'There is already a layer with shortname "{}" '
                'for this stack'.format(shortname))
        layer = Layer(**kwargs)
        self.layers[layer.id] = layer
        self.stacks[stackid].layers.append(layer)
        return layer

    def describe_stacks(self, stack_ids):
        if stack_ids is None:
            return [stack.to_dict() for stack in self.stacks.values()]

        unknown_stacks = set(stack_ids) - set(self.stacks.keys())
        if unknown_stacks:
            raise ResourceNotFoundException(", ".join(unknown_stacks))
        return [self.stacks[id].to_dict() for id in stack_ids]

    def describe_layers(self, stack_id, layer_ids):
        if stack_id is not None and layer_ids is not None:
            raise ValidationException(
                "Please provide one or more layer IDs or a stack ID"
            )
        if stack_id is not None:
            if stack_id not in self.stacks:
                raise ResourceNotFoundException(
                    "Unable to find stack with ID {}".format(stack_id))
            return [layer.to_dict() for layer in self.stacks[stack_id].layers]

        unknown_layers = set(layer_ids) - set(self.layers.keys())
        if unknown_layers:
            raise ResourceNotFoundException(", ".join(unknown_layers))
        return [self.layers[id].to_dict() for id in layer_ids]



opsworks_backends = {}
for region, ec2_backend in ec2_backends.items():
    opsworks_backends[region] = OpsWorksBackend(ec2_backend, elb_backends[region])
