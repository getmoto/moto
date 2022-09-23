from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends
from moto.core.utils import BackendDict
from moto.moto_api._internal import mock_random as random
import datetime

from .exceptions import ResourceNotFoundException, ValidationException


class OpsworkInstance(BaseModel):
    """
    opsworks maintains its own set of ec2 instance metadata.
    This metadata exists before any instance reservations are made, and is
    used to populate a reservation request when "start" is called
    """

    def __init__(
        self,
        stack_id,
        layer_ids,
        instance_type,
        ec2_backend,
        auto_scale_type=None,
        hostname=None,
        os=None,
        ami_id="ami-08111162",
        ssh_keyname=None,
        availability_zone=None,
        virtualization_type="hvm",
        subnet_id=None,
        architecture="x86_64",
        root_device_type="ebs",
        block_device_mappings=None,
        install_updates_on_boot=True,
        ebs_optimized=False,
        agent_version="INHERIT",
        instance_profile_arn=None,
        associate_public_ip=None,
        security_group_ids=None,
    ):

        self.ec2_backend = ec2_backend

        self.instance_profile_arn = instance_profile_arn
        self.agent_version = agent_version
        self.ebs_optimized = ebs_optimized
        self.install_updates_on_boot = install_updates_on_boot
        self.architecture = architecture
        self.virtualization_type = virtualization_type
        self.ami_id = ami_id
        self.auto_scale_type = auto_scale_type
        self.instance_type = instance_type
        self.layer_ids = layer_ids
        self.stack_id = stack_id

        # may not be totally accurate defaults; instance-type dependent
        self.root_device_type = root_device_type
        # todo: refactor how we track block_device_mappings to use
        # boto.ec2.blockdevicemapping.BlockDeviceType and standardize
        # formatting in to_dict()
        self.block_device_mappings = block_device_mappings
        if self.block_device_mappings is None:
            self.block_device_mappings = [
                {
                    "DeviceName": "ROOT_DEVICE",
                    "Ebs": {"VolumeSize": 8, "VolumeType": "gp2"},
                }
            ]
        self.security_group_ids = security_group_ids
        if self.security_group_ids is None:
            self.security_group_ids = []

        self.os = os
        self.hostname = hostname
        self.ssh_keyname = ssh_keyname
        self.availability_zone = availability_zone
        self.subnet_id = subnet_id
        self.associate_public_ip = associate_public_ip

        self.instance = None
        self.reported_os = {}
        self.infrastructure_class = "ec2 (fixed)"
        self.platform = "linux (fixed)"

        self.id = "{0}".format(random.uuid4())
        self.created_at = datetime.datetime.utcnow()

    def start(self):
        """
        create an ec2 reservation if one doesn't already exist and call
        start_instance. Update instance attributes to the newly created instance
        attributes
        """
        if self.instance is None:
            reservation = self.ec2_backend.add_instances(
                image_id=self.ami_id,
                count=1,
                user_data="",
                security_group_names=[],
                security_group_ids=self.security_group_ids,
                instance_type=self.instance_type,
                is_instance_type_default=not self.instance_type,
                key_name=self.ssh_keyname,
                ebs_optimized=self.ebs_optimized,
                subnet_id=self.subnet_id,
                associate_public_ip=self.associate_public_ip,
            )
            self.instance = reservation.instances[0]
            self.reported_os = {
                "Family": "rhel (fixed)",
                "Name": "amazon (fixed)",
                "Version": "2016.03 (fixed)",
            }
            self.platform = self.instance.platform
            self.security_group_ids = self.instance.security_groups
            self.architecture = self.instance.architecture
            self.virtualization_type = self.instance.virtualization_type
            self.subnet_id = self.instance.subnet_id
            self.root_device_type = self.instance.root_device_type

        self.ec2_backend.start_instances([self.instance.id])

    @property
    def status(self):
        if self.instance is None:
            return "stopped"
        # OpsWorks reports the "running" state as "online"
        elif self.instance._state.name == "running":
            return "online"
        return self.instance._state.name

    def to_dict(self):
        d = {
            "AgentVersion": self.agent_version,
            "Architecture": self.architecture,
            "AvailabilityZone": self.availability_zone,
            "BlockDeviceMappings": self.block_device_mappings,
            "CreatedAt": self.created_at.isoformat(),
            "EbsOptimized": self.ebs_optimized,
            "InstanceId": self.id,
            "Hostname": self.hostname,
            "InfrastructureClass": self.infrastructure_class,
            "InstallUpdatesOnBoot": self.install_updates_on_boot,
            "InstanceProfileArn": self.instance_profile_arn,
            "InstanceType": self.instance_type,
            "LayerIds": self.layer_ids,
            "Os": self.os,
            "Platform": self.platform,
            "ReportedOs": self.reported_os,
            "RootDeviceType": self.root_device_type,
            "SecurityGroupIds": self.security_group_ids,
            "AmiId": self.ami_id,
            "Status": self.status,
        }
        if self.ssh_keyname is not None:
            d.update({"SshKeyName": self.ssh_keyname})

        if self.auto_scale_type is not None:
            d.update({"AutoScaleType": self.auto_scale_type})

        if self.instance is not None:
            d.update({"Ec2InstanceId": self.instance.id})
            d.update({"ReportedAgentVersion": "2425-20160406102508 (fixed)"})
            d.update({"RootDeviceVolumeId": "vol-a20e450a (fixed)"})
            if self.ssh_keyname is not None:
                d.update(
                    {
                        "SshHostDsaKeyFingerprint": "24:36:32:fe:d8:5f:9c:18:b1:ad:37:e9:eb:e8:69:58 (fixed)"
                    }
                )
                d.update(
                    {
                        "SshHostRsaKeyFingerprint": "3c:bd:37:52:d7:ca:67:e1:6e:4b:ac:31:86:79:f5:6c (fixed)"
                    }
                )
            d.update({"PrivateDns": self.instance.private_dns})
            d.update({"PrivateIp": self.instance.private_ip})
            d.update({"PublicDns": getattr(self.instance, "public_dns", None)})
            d.update({"PublicIp": getattr(self.instance, "public_ip", None)})
        return d


class Layer(BaseModel):
    def __init__(
        self,
        stack_id,
        layer_type,
        name,
        shortname,
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
        lifecycle_event_configuration=None,
    ):
        self.stack_id = stack_id
        self.type = layer_type
        self.name = name
        self.shortname = shortname

        self.attributes = attributes
        if attributes is None:
            self.attributes = {
                "BundlerVersion": None,
                "EcsClusterArn": None,
                "EnableHaproxyStats": None,
                "GangliaPassword": None,
                "GangliaUrl": None,
                "GangliaUser": None,
                "HaproxyHealthCheckMethod": None,
                "HaproxyHealthCheckUrl": None,
                "HaproxyStatsPassword": None,
                "HaproxyStatsUrl": None,
                "HaproxyStatsUser": None,
                "JavaAppServer": None,
                "JavaAppServerVersion": None,
                "Jvm": None,
                "JvmOptions": None,
                "JvmVersion": None,
                "ManageBundler": None,
                "MemcachedMemory": None,
                "MysqlRootPassword": None,
                "MysqlRootPasswordUbiquitous": None,
                "NodejsVersion": None,
                "PassengerVersion": None,
                "RailsStack": None,
                "RubyVersion": None,
                "RubygemsVersion": None,
            }  # May not be accurate

        self.packages = packages
        if packages is None:
            self.packages = packages

        self.custom_recipes = custom_recipes
        if custom_recipes is None:
            self.custom_recipes = {
                "Configure": [],
                "Deploy": [],
                "Setup": [],
                "Shutdown": [],
                "Undeploy": [],
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

        self.id = "{0}".format(random.uuid4())
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
                "Undeploy": [],
            },  # May not be accurate
            "DefaultSecurityGroupNames": ["AWS-OpsWorks-Custom-Server"],
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


class Stack(BaseModel):
    def __init__(
        self,
        name,
        account_id,
        region,
        service_role_arn,
        default_instance_profile_arn,
        vpcid="vpc-1f99bf7a",
        attributes=None,
        default_os="Ubuntu 12.04 LTS",
        hostname_theme="Layer_Dependent",
        default_availability_zone="us-east-1a",
        default_subnet_id="subnet-73981004",
        custom_json=None,
        configuration_manager=None,
        chef_configuration=None,
        use_custom_cookbooks=False,
        use_opsworks_security_groups=True,
        custom_cookbooks_source=None,
        default_ssh_keyname=None,
        default_root_device_type="instance-store",
        agent_version="LATEST",
    ):

        self.name = name
        self.region = region
        self.service_role_arn = service_role_arn
        self.default_instance_profile_arn = default_instance_profile_arn

        self.vpcid = vpcid
        self.attributes = attributes
        if attributes is None:
            self.attributes = {"Color": None}

        self.configuration_manager = configuration_manager
        if configuration_manager is None:
            self.configuration_manager = {"Name": "Chef", "Version": "11.4"}

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

        self.id = "{0}".format(random.uuid4())
        self.layers = []
        self.apps = []
        self.account_number = account_id
        self.created_at = datetime.datetime.utcnow()

    def __eq__(self, other):
        return self.id == other.id

    def generate_hostname(self):
        # this doesn't match amazon's implementation
        return "{theme}-{rand}-(moto)".format(
            theme=self.hostname_theme,
            rand=[random.choice("abcdefghijhk") for _ in range(4)],
        )

    @property
    def arn(self):
        return "arn:aws:opsworks:{region}:{account_number}:stack/{id}".format(
            region=self.region, account_number=self.account_number, id=self.id
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
            "VpcId": self.vpcid,
        }
        if self.custom_json is not None:
            response.update({"CustomJson": self.custom_json})
        if self.default_ssh_keyname is not None:
            response.update({"DefaultSshKeyName": self.default_ssh_keyname})
        return response


class App(BaseModel):
    def __init__(
        self,
        stack_id,
        name,
        app_type,
        shortname=None,
        description=None,
        datasources=None,
        app_source=None,
        domains=None,
        enable_ssl=False,
        ssl_configuration=None,
        attributes=None,
        environment=None,
    ):
        self.stack_id = stack_id
        self.name = name
        self.type = app_type
        self.shortname = shortname
        self.description = description

        self.datasources = datasources
        if datasources is None:
            self.datasources = []

        self.app_source = app_source
        if app_source is None:
            self.app_source = {}

        self.domains = domains
        if domains is None:
            self.domains = []

        self.enable_ssl = enable_ssl

        self.ssl_configuration = ssl_configuration
        if ssl_configuration is None:
            self.ssl_configuration = {}

        self.attributes = attributes
        if attributes is None:
            self.attributes = {}

        self.environment = environment
        if environment is None:
            self.environment = {}

        self.id = "{0}".format(random.uuid4())
        self.created_at = datetime.datetime.utcnow()

    def __eq__(self, other):
        return self.id == other.id

    def to_dict(self):
        d = {
            "AppId": self.id,
            "AppSource": self.app_source,
            "Attributes": self.attributes,
            "CreatedAt": self.created_at.isoformat(),
            "Datasources": self.datasources,
            "Description": self.description,
            "Domains": self.domains,
            "EnableSsl": self.enable_ssl,
            "Environment": self.environment,
            "Name": self.name,
            "Shortname": self.shortname,
            "SslConfiguration": self.ssl_configuration,
            "StackId": self.stack_id,
            "Type": self.type,
        }
        return d


class OpsWorksBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.stacks = {}
        self.layers = {}
        self.apps = {}
        self.instances = {}
        self.ec2_backend = ec2_backends[account_id][region_name]

    def create_stack(self, **kwargs):
        stack = Stack(account_id=self.account_id, **kwargs)
        self.stacks[stack.id] = stack
        return stack

    def create_layer(self, **kwargs):
        name = kwargs["name"]
        shortname = kwargs["shortname"]
        stackid = kwargs["stack_id"]
        if stackid not in self.stacks:
            raise ResourceNotFoundException(stackid)
        if name in [layer.name for layer in self.stacks[stackid].layers]:
            raise ValidationException(
                'There is already a layer named "{0}" ' "for this stack".format(name)
            )
        if shortname in [layer.shortname for layer in self.stacks[stackid].layers]:
            raise ValidationException(
                'There is already a layer with shortname "{0}" '
                "for this stack".format(shortname)
            )
        layer = Layer(**kwargs)
        self.layers[layer.id] = layer
        self.stacks[stackid].layers.append(layer)
        return layer

    def create_app(self, **kwargs):
        name = kwargs["name"]
        stackid = kwargs["stack_id"]
        if stackid not in self.stacks:
            raise ResourceNotFoundException(stackid)
        if name in [a.name for a in self.stacks[stackid].apps]:
            raise ValidationException(
                'There is already an app named "{0}" ' "for this stack".format(name)
            )
        app = App(**kwargs)
        self.apps[app.id] = app
        self.stacks[stackid].apps.append(app)
        return app

    def create_instance(self, **kwargs):
        stack_id = kwargs["stack_id"]
        layer_ids = kwargs["layer_ids"]

        if stack_id not in self.stacks:
            raise ResourceNotFoundException(
                "Unable to find stack with ID {0}".format(stack_id)
            )

        unknown_layers = set(layer_ids) - set(self.layers.keys())
        if unknown_layers:
            raise ResourceNotFoundException(", ".join(unknown_layers))

        layers = [self.layers[id] for id in layer_ids]
        if len(set([layer.stack_id for layer in layers])) != 1 or any(
            [layer.stack_id != stack_id for layer in layers]
        ):
            raise ValidationException(
                "Please only provide layer IDs from the same stack"
            )

        stack = self.stacks[stack_id]
        # pick the first to set default instance_profile_arn and
        # security_group_ids on the instance.
        layer = layers[0]

        kwargs.setdefault("hostname", stack.generate_hostname())
        kwargs.setdefault("ssh_keyname", stack.default_ssh_keyname)
        kwargs.setdefault("availability_zone", stack.default_availability_zone)
        kwargs.setdefault("subnet_id", stack.default_subnet_id)
        kwargs.setdefault("root_device_type", stack.default_root_device_type)
        if layer.custom_instance_profile_arn:
            kwargs.setdefault("instance_profile_arn", layer.custom_instance_profile_arn)
        kwargs.setdefault("instance_profile_arn", stack.default_instance_profile_arn)
        kwargs.setdefault("security_group_ids", layer.custom_security_group_ids)
        kwargs.setdefault("associate_public_ip", layer.auto_assign_public_ips)
        kwargs.setdefault("ebs_optimized", layer.use_ebs_optimized_instances)
        kwargs.update({"ec2_backend": self.ec2_backend})
        opsworks_instance = OpsworkInstance(**kwargs)
        self.instances[opsworks_instance.id] = opsworks_instance
        return opsworks_instance

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
                    "Unable to find stack with ID {0}".format(stack_id)
                )
            return [layer.to_dict() for layer in self.stacks[stack_id].layers]

        unknown_layers = set(layer_ids) - set(self.layers.keys())
        if unknown_layers:
            raise ResourceNotFoundException(", ".join(unknown_layers))
        return [self.layers[id].to_dict() for id in layer_ids]

    def describe_apps(self, stack_id, app_ids):
        if stack_id is not None and app_ids is not None:
            raise ValidationException(
                "Please provide one or more app IDs or a stack ID"
            )
        if stack_id is not None:
            if stack_id not in self.stacks:
                raise ResourceNotFoundException(
                    "Unable to find stack with ID {0}".format(stack_id)
                )
            return [app.to_dict() for app in self.stacks[stack_id].apps]

        unknown_apps = set(app_ids) - set(self.apps.keys())
        if unknown_apps:
            raise ResourceNotFoundException(", ".join(unknown_apps))
        return [self.apps[id].to_dict() for id in app_ids]

    def describe_instances(self, instance_ids, layer_id, stack_id):
        if len(list(filter(None, (instance_ids, layer_id, stack_id)))) != 1:
            raise ValidationException(
                "Please provide either one or more "
                "instance IDs or one stack ID or one "
                "layer ID"
            )
        if instance_ids:
            unknown_instances = set(instance_ids) - set(self.instances.keys())
            if unknown_instances:
                raise ResourceNotFoundException(", ".join(unknown_instances))
            return [self.instances[id].to_dict() for id in instance_ids]

        if layer_id:
            if layer_id not in self.layers:
                raise ResourceNotFoundException(
                    "Unable to find layer with ID {0}".format(layer_id)
                )
            instances = [
                i.to_dict() for i in self.instances.values() if layer_id in i.layer_ids
            ]
            return instances

        if stack_id:
            if stack_id not in self.stacks:
                raise ResourceNotFoundException(
                    "Unable to find stack with ID {0}".format(stack_id)
                )
            instances = [
                i.to_dict() for i in self.instances.values() if stack_id == i.stack_id
            ]
            return instances

    def start_instance(self, instance_id):
        if instance_id not in self.instances:
            raise ResourceNotFoundException(
                "Unable to find instance with ID {0}".format(instance_id)
            )
        self.instances[instance_id].start()


opsworks_backends = BackendDict(OpsWorksBackend, "ec2")
