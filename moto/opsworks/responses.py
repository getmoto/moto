from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import opsworks_backends


class OpsWorksResponse(BaseResponse):

    @property
    def parameters(self):
        return json.loads(self.body.decode("utf-8"))

    @property
    def opsworks_backend(self):
        return opsworks_backends[self.region]

    def create_stack(self):
        kwargs = dict(
            name=self.parameters.get("Name"),
            region=self.parameters.get("Region"),
            vpcid=self.parameters.get("VpcId"),
            attributes=self.parameters.get("Attributes"),
            default_instance_profile_arn=self.parameters.get("DefaultInstanceProfileArn"),
            default_os=self.parameters.get("DefaultOs"),
            hostname_theme=self.parameters.get("HostnameTheme"),
            default_availability_zone=self.parameters.get("DefaultAvailabilityZone"),
            default_subnet_id=self.parameters.get("DefaultInstanceProfileArn"),
            custom_json=self.parameters.get("CustomJson"),
            configuration_manager=self.parameters.get("ConfigurationManager"),
            chef_configuration=self.parameters.get("ChefConfiguration"),
            use_custom_cookbooks=self.parameters.get("UseCustomCookbooks"),
            use_opsworks_security_groups=self.parameters.get("UseOpsworksSecurityGroups"),
            custom_cookbooks_source=self.parameters.get("CustomCookbooksSource"),
            default_ssh_keyname=self.parameters.get("DefaultSshKeyName"),
            default_root_device_type=self.parameters.get("DefaultRootDeviceType"),
            service_role_arn=self.parameters.get("ServiceRoleArn"),
            agent_version=self.parameters.get("AgentVersion"),
        )
        stack = self.opsworks_backend.create_stack(**kwargs)
        return json.dumps({"StackId": stack.id}, indent=1)

    def describe_stacks(self):
        stack_ids = self.parameters.get("StackIds")
        stacks = self.opsworks_backend.describe_stacks(stack_ids)
        return json.dumps({"Stacks": stacks}, indent=1)
