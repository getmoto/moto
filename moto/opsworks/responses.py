import json

from moto.core.responses import BaseResponse
from .models import opsworks_backends


class OpsWorksResponse(BaseResponse):
    @property
    def parameters(self):
        return json.loads(self.body)

    @property
    def opsworks_backend(self):
        return opsworks_backends[self.region]

    def create_stack(self):
        kwargs = dict(
            name=self.parameters.get("Name"),
            region=self.parameters.get("Region"),
            vpcid=self.parameters.get("VpcId"),
            attributes=self.parameters.get("Attributes"),
            default_instance_profile_arn=self.parameters.get(
                "DefaultInstanceProfileArn"
            ),
            default_os=self.parameters.get("DefaultOs"),
            hostname_theme=self.parameters.get("HostnameTheme"),
            default_availability_zone=self.parameters.get("DefaultAvailabilityZone"),
            default_subnet_id=self.parameters.get("DefaultInstanceProfileArn"),
            custom_json=self.parameters.get("CustomJson"),
            configuration_manager=self.parameters.get("ConfigurationManager"),
            chef_configuration=self.parameters.get("ChefConfiguration"),
            use_custom_cookbooks=self.parameters.get("UseCustomCookbooks"),
            use_opsworks_security_groups=self.parameters.get(
                "UseOpsworksSecurityGroups"
            ),
            custom_cookbooks_source=self.parameters.get("CustomCookbooksSource"),
            default_ssh_keyname=self.parameters.get("DefaultSshKeyName"),
            default_root_device_type=self.parameters.get("DefaultRootDeviceType"),
            service_role_arn=self.parameters.get("ServiceRoleArn"),
            agent_version=self.parameters.get("AgentVersion"),
        )
        stack = self.opsworks_backend.create_stack(**kwargs)
        return json.dumps({"StackId": stack.id}, indent=1)

    def create_layer(self):
        kwargs = dict(
            stack_id=self.parameters.get("StackId"),
            layer_type=self.parameters.get("Type"),
            name=self.parameters.get("Name"),
            shortname=self.parameters.get("Shortname"),
            attributes=self.parameters.get("Attributes"),
            custom_instance_profile_arn=self.parameters.get("CustomInstanceProfileArn"),
            custom_json=self.parameters.get("CustomJson"),
            custom_security_group_ids=self.parameters.get("CustomSecurityGroupIds"),
            packages=self.parameters.get("Packages"),
            volume_configurations=self.parameters.get("VolumeConfigurations"),
            enable_autohealing=self.parameters.get("EnableAutoHealing"),
            auto_assign_elastic_ips=self.parameters.get("AutoAssignElasticIps"),
            auto_assign_public_ips=self.parameters.get("AutoAssignPublicIps"),
            custom_recipes=self.parameters.get("CustomRecipes"),
            install_updates_on_boot=self.parameters.get("InstallUpdatesOnBoot"),
            use_ebs_optimized_instances=self.parameters.get("UseEbsOptimizedInstances"),
            lifecycle_event_configuration=self.parameters.get(
                "LifecycleEventConfiguration"
            ),
        )
        layer = self.opsworks_backend.create_layer(**kwargs)
        return json.dumps({"LayerId": layer.id}, indent=1)

    def create_app(self):
        kwargs = dict(
            stack_id=self.parameters.get("StackId"),
            name=self.parameters.get("Name"),
            app_type=self.parameters.get("Type"),
            shortname=self.parameters.get("Shortname"),
            description=self.parameters.get("Description"),
            datasources=self.parameters.get("DataSources"),
            app_source=self.parameters.get("AppSource"),
            domains=self.parameters.get("Domains"),
            enable_ssl=self.parameters.get("EnableSsl"),
            ssl_configuration=self.parameters.get("SslConfiguration"),
            attributes=self.parameters.get("Attributes"),
            environment=self.parameters.get("Environment"),
        )
        app = self.opsworks_backend.create_app(**kwargs)
        return json.dumps({"AppId": app.id}, indent=1)

    def create_instance(self):
        kwargs = dict(
            stack_id=self.parameters.get("StackId"),
            layer_ids=self.parameters.get("LayerIds"),
            instance_type=self.parameters.get("InstanceType"),
            auto_scale_type=self.parameters.get("AutoScalingType"),
            hostname=self.parameters.get("Hostname"),
            os=self.parameters.get("Os"),
            ami_id=self.parameters.get("AmiId"),
            ssh_keyname=self.parameters.get("SshKeyName"),
            availability_zone=self.parameters.get("AvailabilityZone"),
            virtualization_type=self.parameters.get("VirtualizationType"),
            subnet_id=self.parameters.get("SubnetId"),
            architecture=self.parameters.get("Architecture"),
            root_device_type=self.parameters.get("RootDeviceType"),
            block_device_mappings=self.parameters.get("BlockDeviceMappings"),
            install_updates_on_boot=self.parameters.get("InstallUpdatesOnBoot"),
            ebs_optimized=self.parameters.get("EbsOptimized"),
            agent_version=self.parameters.get("AgentVersion"),
        )
        opsworks_instance = self.opsworks_backend.create_instance(**kwargs)
        return json.dumps({"InstanceId": opsworks_instance.id}, indent=1)

    def describe_stacks(self):
        stack_ids = self.parameters.get("StackIds")
        stacks = self.opsworks_backend.describe_stacks(stack_ids)
        return json.dumps({"Stacks": stacks}, indent=1)

    def describe_layers(self):
        stack_id = self.parameters.get("StackId")
        layer_ids = self.parameters.get("LayerIds")
        layers = self.opsworks_backend.describe_layers(stack_id, layer_ids)
        return json.dumps({"Layers": layers}, indent=1)

    def describe_apps(self):
        stack_id = self.parameters.get("StackId")
        app_ids = self.parameters.get("AppIds")
        apps = self.opsworks_backend.describe_apps(stack_id, app_ids)
        return json.dumps({"Apps": apps}, indent=1)

    def describe_instances(self):
        instance_ids = self.parameters.get("InstanceIds")
        layer_id = self.parameters.get("LayerId")
        stack_id = self.parameters.get("StackId")
        instances = self.opsworks_backend.describe_instances(
            instance_ids, layer_id, stack_id
        )
        return json.dumps({"Instances": instances}, indent=1)

    def start_instance(self):
        instance_id = self.parameters.get("InstanceId")
        self.opsworks_backend.start_instance(instance_id)
        return ""
