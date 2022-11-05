import itertools
from typing import Any, Dict, List, Optional, Tuple, Union

from moto.packages.boto.ec2.blockdevicemapping import (
    BlockDeviceType,
    BlockDeviceMapping,
)
from moto.ec2.exceptions import InvalidInstanceIdError

from collections import OrderedDict
from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import camelcase_to_underscores, BackendDict
from moto.ec2 import ec2_backends
from moto.ec2.models import EC2Backend
from moto.ec2.models.instances import Instance
from moto.elb.models import elb_backends, ELBBackend
from moto.elbv2.models import elbv2_backends, ELBv2Backend
from moto.elb.exceptions import LoadBalancerNotFoundError
from moto.moto_api._internal import mock_random as random
from .exceptions import (
    AutoscalingClientError,
    ResourceContentionError,
    InvalidInstanceError,
    ValidationError,
)

# http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/AS_Concepts.html#Cooldown
DEFAULT_COOLDOWN = 300

ASG_NAME_TAG = "aws:autoscaling:groupName"


class InstanceState(object):
    def __init__(
        self,
        instance: "Instance",
        lifecycle_state: str = "InService",
        health_status: str = "Healthy",
        protected_from_scale_in: Optional[bool] = False,
        autoscaling_group: Optional["FakeAutoScalingGroup"] = None,
    ):
        self.instance = instance
        self.lifecycle_state = lifecycle_state
        self.health_status = health_status
        self.protected_from_scale_in = protected_from_scale_in
        if not hasattr(self.instance, "autoscaling_group"):
            self.instance.autoscaling_group = autoscaling_group  # type: ignore[attr-defined]


class FakeLifeCycleHook(BaseModel):
    def __init__(
        self,
        name: str,
        as_name: str,
        transition: Optional[str],
        timeout: Optional[int],
        result: Optional[str],
    ):
        self.name = name
        self.as_name = as_name
        if transition:
            self.transition = transition
        if timeout:
            self.timeout = timeout
        else:
            self.timeout = 3600
        if result:
            self.result = result
        else:
            self.result = "ABANDON"


class FakeScalingPolicy(BaseModel):
    def __init__(
        self,
        name: str,
        policy_type: str,
        metric_aggregation_type: str,
        adjustment_type: str,
        as_name: str,
        min_adjustment_magnitude: str,
        scaling_adjustment: Optional[int],
        cooldown: Optional[int],
        target_tracking_config: str,
        step_adjustments: str,
        estimated_instance_warmup: str,
        predictive_scaling_configuration: str,
        autoscaling_backend: "AutoScalingBackend",
    ):
        self.name = name
        self.policy_type = policy_type
        self.metric_aggregation_type = metric_aggregation_type
        self.adjustment_type = adjustment_type
        self.as_name = as_name
        self.min_adjustment_magnitude = min_adjustment_magnitude
        self.scaling_adjustment = scaling_adjustment
        if cooldown is not None:
            self.cooldown = cooldown
        else:
            self.cooldown = DEFAULT_COOLDOWN
        self.target_tracking_config = target_tracking_config
        self.step_adjustments = step_adjustments
        self.estimated_instance_warmup = estimated_instance_warmup
        self.predictive_scaling_configuration = predictive_scaling_configuration
        self.autoscaling_backend = autoscaling_backend

    @property
    def arn(self) -> str:
        return f"arn:aws:autoscaling:{self.autoscaling_backend.region_name}:{self.autoscaling_backend.account_id}:scalingPolicy:c322761b-3172-4d56-9a21-0ed9d6161d67:autoScalingGroupName/{self.as_name}:policyName/{self.name}"

    def execute(self) -> None:
        if self.adjustment_type == "ExactCapacity":
            self.autoscaling_backend.set_desired_capacity(
                self.as_name, self.scaling_adjustment
            )
        elif self.adjustment_type == "ChangeInCapacity":
            self.autoscaling_backend.change_capacity(
                self.as_name, self.scaling_adjustment
            )
        elif self.adjustment_type == "PercentChangeInCapacity":
            self.autoscaling_backend.change_capacity_percent(
                self.as_name, self.scaling_adjustment
            )


class FakeLaunchConfiguration(CloudFormationModel):
    def __init__(
        self,
        name: str,
        image_id: str,
        key_name: Optional[str],
        ramdisk_id: str,
        kernel_id: str,
        security_groups: List[str],
        user_data: str,
        instance_type: str,
        instance_monitoring: bool,
        instance_profile_name: Optional[str],
        spot_price: Optional[str],
        ebs_optimized: str,
        associate_public_ip_address: Union[str, bool],
        block_device_mapping_dict: List[Dict[str, Any]],
        account_id: str,
        region_name: str,
        metadata_options: Optional[str],
        classic_link_vpc_id: Optional[str],
        classic_link_vpc_security_groups: Optional[str],
    ):
        self.name = name
        self.image_id = image_id
        self.key_name = key_name
        self.ramdisk_id = ramdisk_id
        self.kernel_id = kernel_id
        self.security_groups = security_groups if security_groups else []
        self.user_data = user_data
        self.instance_type = instance_type
        self.instance_monitoring = instance_monitoring
        self.instance_profile_name = instance_profile_name
        self.spot_price = spot_price
        self.ebs_optimized = ebs_optimized
        if isinstance(associate_public_ip_address, str):
            self.associate_public_ip_address = (
                associate_public_ip_address.lower() == "true"
            )
        else:
            self.associate_public_ip_address = associate_public_ip_address
        self.block_device_mapping_dict = block_device_mapping_dict
        self.metadata_options = metadata_options
        self.classic_link_vpc_id = classic_link_vpc_id
        self.classic_link_vpc_security_groups = classic_link_vpc_security_groups
        self.arn = f"arn:aws:autoscaling:{region_name}:{account_id}:launchConfiguration:9dbbbf87-6141-428a-a409-0752edbe6cad:launchConfigurationName/{self.name}"

    @classmethod
    def create_from_instance(
        cls, name: str, instance: Instance, backend: "AutoScalingBackend"
    ) -> "FakeLaunchConfiguration":
        config = backend.create_launch_configuration(
            name=name,
            image_id=instance.image_id,
            kernel_id="",
            ramdisk_id="",
            key_name=instance.key_name,
            security_groups=instance.security_groups,
            user_data=instance.user_data,
            instance_type=instance.instance_type,
            instance_monitoring=False,
            instance_profile_name=None,
            spot_price=None,
            ebs_optimized=instance.ebs_optimized,
            associate_public_ip_address=instance.associate_public_ip,
            # We expect a dictionary in the same format as when the user calls it
            block_device_mappings=instance.block_device_mapping.to_source_dict(),
        )
        return config

    @staticmethod
    def cloudformation_name_type() -> str:
        return "LaunchConfigurationName"

    @staticmethod
    def cloudformation_type() -> str:
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-autoscaling-launchconfiguration.html
        return "AWS::AutoScaling::LaunchConfiguration"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Any,
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "FakeLaunchConfiguration":
        properties = cloudformation_json["Properties"]

        instance_profile_name = properties.get("IamInstanceProfile")

        backend = autoscaling_backends[account_id][region_name]
        config = backend.create_launch_configuration(
            name=resource_name,
            image_id=properties.get("ImageId"),
            kernel_id=properties.get("KernelId"),
            ramdisk_id=properties.get("RamdiskId"),
            key_name=properties.get("KeyName"),
            security_groups=properties.get("SecurityGroups"),
            user_data=properties.get("UserData"),
            instance_type=properties.get("InstanceType"),
            instance_monitoring=properties.get("InstanceMonitoring"),
            instance_profile_name=instance_profile_name,
            spot_price=properties.get("SpotPrice"),
            ebs_optimized=properties.get("EbsOptimized"),
            associate_public_ip_address=properties.get("AssociatePublicIpAddress"),
            block_device_mappings=properties.get("BlockDeviceMapping.member"),
        )
        return config

    @classmethod
    def update_from_cloudformation_json(  # type: ignore[misc]
        cls,
        original_resource: Any,
        new_resource_name: str,
        cloudformation_json: Any,
        account_id: str,
        region_name: str,
    ) -> "FakeLaunchConfiguration":
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, account_id, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, account_id, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Any,
        account_id: str,
        region_name: str,
    ) -> None:
        backend = autoscaling_backends[account_id][region_name]
        try:
            backend.delete_launch_configuration(resource_name)
        except KeyError:
            pass

    def delete(self, account_id: str, region_name: str) -> None:
        backend = autoscaling_backends[account_id][region_name]
        backend.delete_launch_configuration(self.name)

    @property
    def physical_resource_id(self) -> str:
        return self.name

    @property
    def block_device_mappings(self) -> Optional[BlockDeviceMapping]:
        if not self.block_device_mapping_dict:
            return None
        else:
            return self._parse_block_device_mappings()

    @property
    def instance_monitoring_enabled(self) -> str:
        if self.instance_monitoring:
            return "true"
        return "false"

    def _parse_block_device_mappings(self) -> BlockDeviceMapping:
        block_device_map = BlockDeviceMapping()
        for mapping in self.block_device_mapping_dict:
            block_type = BlockDeviceType()
            mount_point = mapping.get("DeviceName")
            if mapping.get("VirtualName") and "ephemeral" in mapping.get("VirtualName"):  # type: ignore[operator]
                block_type.ephemeral_name = mapping.get("VirtualName")
            elif mapping.get("NoDevice", "false") == "true":
                block_type.no_device = "true"
            else:
                ebs = mapping.get("Ebs", {})
                block_type.volume_type = ebs.get("VolumeType")
                block_type.snapshot_id = ebs.get("SnapshotId")
                block_type.delete_on_termination = ebs.get("DeleteOnTermination")
                block_type.size = ebs.get("VolumeSize")
                block_type.iops = ebs.get("Iops")
                block_type.throughput = ebs.get("Throughput")
                block_type.encrypted = ebs.get("Encrypted")
            block_device_map[mount_point] = block_type
        return block_device_map


class FakeScheduledAction(CloudFormationModel):
    def __init__(
        self,
        name: str,
        desired_capacity: Optional[int],
        max_size: Optional[int],
        min_size: Optional[int],
        scheduled_action_name: str,
        start_time: str,
        end_time: str,
        recurrence: str,
    ):

        self.name = name
        self.desired_capacity = desired_capacity
        self.max_size = max_size
        self.min_size = min_size
        self.start_time = start_time
        self.end_time = end_time
        self.recurrence = recurrence
        self.scheduled_action_name = scheduled_action_name

    @staticmethod
    def cloudformation_name_type() -> str:
        return "ScheduledActionName"

    @staticmethod
    def cloudformation_type() -> str:
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-as-scheduledaction.html
        return "AWS::AutoScaling::ScheduledAction"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "FakeScheduledAction":

        properties = cloudformation_json["Properties"]

        backend = autoscaling_backends[account_id][region_name]

        scheduled_action_name = (
            kwargs["LogicalId"]
            if kwargs.get("LogicalId")
            else "ScheduledScalingAction-{random.randint(0,100)}"
        )

        scheduled_action = backend.put_scheduled_update_group_action(
            name=properties.get("AutoScalingGroupName"),
            desired_capacity=properties.get("DesiredCapacity"),
            max_size=properties.get("MaxSize"),
            min_size=properties.get("MinSize"),
            scheduled_action_name=scheduled_action_name,
            start_time=properties.get("StartTime"),
            end_time=properties.get("EndTime"),
            recurrence=properties.get("Recurrence"),
        )
        return scheduled_action


def set_string_propagate_at_launch_booleans_on_tags(
    tags: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    bool_to_string = {True: "true", False: "false"}
    for tag in tags:
        if "PropagateAtLaunch" in tag:
            tag["PropagateAtLaunch"] = bool_to_string[tag["PropagateAtLaunch"]]
    return tags


class FakeAutoScalingGroup(CloudFormationModel):
    def __init__(
        self,
        name: str,
        availability_zones: List[str],
        desired_capacity: Optional[int],
        max_size: Optional[int],
        min_size: Optional[int],
        launch_config_name: str,
        launch_template: Dict[str, Any],
        vpc_zone_identifier: str,
        default_cooldown: Optional[int],
        health_check_period: Optional[int],
        health_check_type: Optional[str],
        load_balancers: List[str],
        target_group_arns: List[str],
        placement_group: str,
        termination_policies: str,
        autoscaling_backend: "AutoScalingBackend",
        ec2_backend: EC2Backend,
        tags: List[Dict[str, str]],
        mixed_instance_policy: Optional[Dict[str, Any]],
        capacity_rebalance: bool,
        new_instances_protected_from_scale_in: bool = False,
    ):
        self.autoscaling_backend = autoscaling_backend
        self.ec2_backend = ec2_backend
        self.name = name
        self._id = str(random.uuid4())
        self.region = self.autoscaling_backend.region_name
        self.account_id = self.autoscaling_backend.account_id
        self.service_linked_role = f"arn:aws:iam::{self.account_id}:role/aws-service-role/autoscaling.amazonaws.com/AWSServiceRoleForAutoScaling"

        self.vpc_zone_identifier: Optional[str] = None
        self._set_azs_and_vpcs(availability_zones, vpc_zone_identifier)

        self.max_size = max_size
        self.min_size = min_size

        self.launch_template = None
        self.launch_config = None

        self._set_launch_configuration(
            launch_config_name, launch_template, mixed_instance_policy
        )
        self.mixed_instance_policy = mixed_instance_policy

        self.default_cooldown = (
            default_cooldown if default_cooldown else DEFAULT_COOLDOWN
        )
        self.health_check_period = health_check_period
        self.health_check_type = health_check_type if health_check_type else "EC2"
        self.load_balancers = load_balancers
        self.target_group_arns = target_group_arns
        self.placement_group = placement_group
        self.capacity_rebalance = capacity_rebalance
        self.termination_policies = termination_policies or ["Default"]
        self.new_instances_protected_from_scale_in = (
            new_instances_protected_from_scale_in
        )

        self.suspended_processes: List[str] = []
        self.instance_states: List[InstanceState] = []
        self.tags: List[Dict[str, str]] = tags or []
        self.set_desired_capacity(desired_capacity)

        self.metrics: List[str] = []

    @property
    def tags(self) -> List[Dict[str, str]]:
        return self._tags

    @tags.setter
    def tags(self, tags: List[Dict[str, str]]) -> None:
        for tag in tags:
            if "resource_id" not in tag or not tag["resource_id"]:
                tag["resource_id"] = self.name
            if "resource_type" not in tag or not tag["resource_type"]:
                tag["resource_type"] = "auto-scaling-group"
        self._tags = tags

    @property
    def arn(self) -> str:
        return f"arn:aws:autoscaling:{self.region}:{self.account_id}:autoScalingGroup:{self._id}:autoScalingGroupName/{self.name}"

    def active_instances(self) -> List[InstanceState]:
        return [x for x in self.instance_states if x.lifecycle_state == "InService"]

    def _set_azs_and_vpcs(
        self,
        availability_zones: List[str],
        vpc_zone_identifier: Optional[str],
        update: bool = False,
    ) -> None:
        # for updates, if only AZs are provided, they must not clash with
        # the AZs of existing VPCs
        if update and availability_zones and not vpc_zone_identifier:
            vpc_zone_identifier = self.vpc_zone_identifier

        if vpc_zone_identifier:
            # extract azs for vpcs
            subnet_ids = vpc_zone_identifier.split(",")
            subnets = self.autoscaling_backend.ec2_backend.get_all_subnets(
                subnet_ids=subnet_ids
            )
            vpc_zones = [subnet.availability_zone for subnet in subnets]

            if availability_zones and set(availability_zones) != set(vpc_zones):
                raise AutoscalingClientError(
                    "ValidationError",
                    "The availability zones of the specified subnets and the Auto Scaling group do not match",
                )
            availability_zones = vpc_zones
        elif not availability_zones:
            if not update:
                raise AutoscalingClientError(
                    "ValidationError",
                    "At least one Availability Zone or VPC Subnet is required.",
                )
            return

        self.availability_zones = availability_zones
        self.vpc_zone_identifier = vpc_zone_identifier

    def _set_launch_configuration(
        self,
        launch_config_name: str,
        launch_template: Dict[str, Any],
        mixed_instance_policy: Optional[Dict[str, Any]],
    ) -> None:
        if launch_config_name:
            self.launch_config = self.autoscaling_backend.launch_configurations[
                launch_config_name
            ]
            self.launch_config_name = launch_config_name

        if launch_template or mixed_instance_policy:
            if launch_template:
                launch_template_id = launch_template.get("launch_template_id")
                launch_template_name = launch_template.get("launch_template_name")
                self.launch_template_version = (
                    launch_template.get("version") or "$Default"
                )
            elif mixed_instance_policy:
                spec = mixed_instance_policy["LaunchTemplate"][
                    "LaunchTemplateSpecification"
                ]
                launch_template_id = spec.get("LaunchTemplateId")
                launch_template_name = spec.get("LaunchTemplateName")
                self.launch_template_version = spec.get("Version") or "$Default"

            if not (launch_template_id or launch_template_name) or (
                launch_template_id and launch_template_name
            ):
                raise ValidationError(
                    "Valid requests must contain either launchTemplateId or LaunchTemplateName"
                )

            if launch_template_id:
                self.launch_template = self.ec2_backend.get_launch_template(
                    launch_template_id
                )
            elif launch_template_name:
                self.launch_template = self.ec2_backend.get_launch_template_by_name(
                    launch_template_name
                )

    @staticmethod
    def cloudformation_name_type() -> str:
        return "AutoScalingGroupName"

    @staticmethod
    def cloudformation_type() -> str:
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-autoscaling-autoscalinggroup.html
        return "AWS::AutoScaling::AutoScalingGroup"

    @classmethod
    def create_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
        **kwargs: Any,
    ) -> "FakeAutoScalingGroup":
        properties = cloudformation_json["Properties"]

        launch_config_name = properties.get("LaunchConfigurationName")
        launch_template = {
            camelcase_to_underscores(k): v
            for k, v in properties.get("LaunchTemplate", {}).items()
        }
        load_balancer_names = properties.get("LoadBalancerNames", [])
        target_group_arns = properties.get("TargetGroupARNs", [])

        backend = autoscaling_backends[account_id][region_name]
        group = backend.create_auto_scaling_group(
            name=resource_name,
            availability_zones=properties.get("AvailabilityZones", []),
            desired_capacity=properties.get("DesiredCapacity"),
            max_size=properties.get("MaxSize"),
            min_size=properties.get("MinSize"),
            launch_config_name=launch_config_name,
            launch_template=launch_template,
            vpc_zone_identifier=(
                ",".join(properties.get("VPCZoneIdentifier", [])) or None
            ),
            default_cooldown=properties.get("Cooldown"),
            health_check_period=properties.get("HealthCheckGracePeriod"),
            health_check_type=properties.get("HealthCheckType"),
            load_balancers=load_balancer_names,
            target_group_arns=target_group_arns,
            placement_group=None,
            termination_policies=properties.get("TerminationPolicies", []),
            tags=set_string_propagate_at_launch_booleans_on_tags(
                properties.get("Tags", [])
            ),
            new_instances_protected_from_scale_in=properties.get(
                "NewInstancesProtectedFromScaleIn", False
            ),
        )
        return group

    @classmethod
    def update_from_cloudformation_json(  # type: ignore[misc]
        cls,
        original_resource: Any,
        new_resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
    ) -> "FakeAutoScalingGroup":
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, account_id, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, account_id, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(  # type: ignore[misc]
        cls,
        resource_name: str,
        cloudformation_json: Dict[str, Any],
        account_id: str,
        region_name: str,
    ) -> None:
        backend = autoscaling_backends[account_id][region_name]
        try:
            backend.delete_auto_scaling_group(resource_name)
        except KeyError:
            pass

    def delete(self, account_id: str, region_name: str) -> None:
        backend = autoscaling_backends[account_id][region_name]
        backend.delete_auto_scaling_group(self.name)

    @property
    def physical_resource_id(self) -> str:
        return self.name

    @property
    def image_id(self) -> str:
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.image_id

        return self.launch_config.image_id  # type: ignore[union-attr]

    @property
    def instance_type(self) -> str:
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.instance_type

        return self.launch_config.instance_type  # type: ignore[union-attr]

    @property
    def user_data(self) -> str:
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.user_data

        return self.launch_config.user_data  # type: ignore[union-attr]

    @property
    def security_groups(self) -> List[str]:
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.security_groups

        return self.launch_config.security_groups  # type: ignore[union-attr]

    def update(
        self,
        availability_zones: List[str],
        desired_capacity: Optional[int],
        max_size: Optional[int],
        min_size: Optional[int],
        launch_config_name: str,
        launch_template: Dict[str, Any],
        vpc_zone_identifier: str,
        health_check_period: int,
        health_check_type: str,
        new_instances_protected_from_scale_in: Optional[bool] = None,
    ) -> None:
        self._set_azs_and_vpcs(availability_zones, vpc_zone_identifier, update=True)

        if max_size is not None:
            self.max_size = max_size
        if min_size is not None:
            self.min_size = min_size

        if desired_capacity is None:
            if min_size is not None and min_size > len(self.instance_states):
                desired_capacity = min_size
            if max_size is not None and max_size < len(self.instance_states):
                desired_capacity = max_size

        self._set_launch_configuration(
            launch_config_name, launch_template, mixed_instance_policy=None
        )

        if health_check_period is not None:
            self.health_check_period = health_check_period
        if health_check_type is not None:
            self.health_check_type = health_check_type
        if new_instances_protected_from_scale_in is not None:
            self.new_instances_protected_from_scale_in = (
                new_instances_protected_from_scale_in
            )

        if desired_capacity is not None:
            self.set_desired_capacity(desired_capacity)

    def set_desired_capacity(self, new_capacity: Optional[int]) -> None:
        if new_capacity is None:
            self.desired_capacity = self.min_size
        else:
            self.desired_capacity = new_capacity

        curr_instance_count = len(self.active_instances())

        if self.desired_capacity == curr_instance_count:
            pass  # Nothing to do here
        elif self.desired_capacity > curr_instance_count:  # type: ignore[operator]
            # Need more instances
            count_needed = int(self.desired_capacity) - int(curr_instance_count)  # type: ignore[arg-type]

            propagated_tags = self.get_propagated_tags()
            self.replace_autoscaling_group_instances(count_needed, propagated_tags)
        else:
            # Need to remove some instances
            count_to_remove = curr_instance_count - self.desired_capacity  # type: ignore[operator]
            instances_to_remove = [  # only remove unprotected
                state
                for state in self.instance_states
                if not state.protected_from_scale_in
            ][:count_to_remove]
            if instances_to_remove:  # just in case not instances to remove
                instance_ids_to_remove = [
                    instance.instance.id for instance in instances_to_remove
                ]
                self.autoscaling_backend.ec2_backend.terminate_instances(
                    instance_ids_to_remove
                )
                self.instance_states = list(
                    set(self.instance_states) - set(instances_to_remove)
                )
        if self.name in self.autoscaling_backend.autoscaling_groups:
            self.autoscaling_backend.update_attached_elbs(self.name)
            self.autoscaling_backend.update_attached_target_groups(self.name)

    def get_propagated_tags(self) -> Dict[str, str]:
        propagated_tags = {}
        for tag in self.tags:
            # boto uses 'propagate_at_launch
            # boto3 and cloudformation use PropagateAtLaunch
            if "propagate_at_launch" in tag and tag["propagate_at_launch"] == "true":
                propagated_tags[tag["key"]] = tag["value"]
            if "PropagateAtLaunch" in tag and tag["PropagateAtLaunch"] == "true":
                propagated_tags[tag["Key"]] = tag["Value"]
        return propagated_tags

    def replace_autoscaling_group_instances(
        self, count_needed: int, propagated_tags: Dict[str, str]
    ) -> None:
        propagated_tags[ASG_NAME_TAG] = self.name

        # VPCZoneIdentifier:
        # A comma-separated list of subnet IDs for a virtual private cloud (VPC) where instances in the Auto Scaling group can be created.
        # We'll create all instances in a single subnet to make things easier
        subnet_id = (
            self.vpc_zone_identifier.split(",")[0] if self.vpc_zone_identifier else None
        )
        associate_public_ip = (
            self.launch_config.associate_public_ip_address
            if self.launch_config
            else None
        )
        reservation = self.autoscaling_backend.ec2_backend.add_instances(
            self.image_id,
            count_needed,
            self.user_data,
            self.security_groups,
            instance_type=self.instance_type,
            tags={"instance": propagated_tags},
            placement=random.choice(self.availability_zones),
            launch_config=self.launch_config,
            is_instance_type_default=False,
            associate_public_ip=associate_public_ip,
            subnet_id=subnet_id,
        )
        for instance in reservation.instances:
            instance.autoscaling_group = self
            self.instance_states.append(
                InstanceState(
                    instance,
                    protected_from_scale_in=self.new_instances_protected_from_scale_in,
                )
            )

    def append_target_groups(self, target_group_arns: List[str]) -> None:
        append = [x for x in target_group_arns if x not in self.target_group_arns]
        self.target_group_arns.extend(append)

    def enable_metrics_collection(self, metrics: List[str]) -> None:
        self.metrics = metrics or []


class AutoScalingBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.autoscaling_groups: Dict[str, FakeAutoScalingGroup] = OrderedDict()
        self.launch_configurations: Dict[str, FakeLaunchConfiguration] = OrderedDict()
        self.scheduled_actions: Dict[str, FakeScheduledAction] = OrderedDict()
        self.policies: Dict[str, FakeScalingPolicy] = {}
        self.lifecycle_hooks: Dict[str, FakeLifeCycleHook] = {}
        self.ec2_backend: EC2Backend = ec2_backends[self.account_id][region_name]
        self.elb_backend: ELBBackend = elb_backends[self.account_id][region_name]
        self.elbv2_backend: ELBv2Backend = elbv2_backends[self.account_id][region_name]

    @staticmethod
    def default_vpc_endpoint_service(service_region: str, zones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:  # type: ignore[misc]
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "autoscaling"
        ) + BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "autoscaling-plans"
        )

    def create_launch_configuration(
        self,
        name: str,
        image_id: str,
        key_name: Optional[str],
        kernel_id: str,
        ramdisk_id: str,
        security_groups: List[str],
        user_data: str,
        instance_type: str,
        instance_monitoring: bool,
        instance_profile_name: Optional[str],
        spot_price: Optional[str],
        ebs_optimized: str,
        associate_public_ip_address: str,
        block_device_mappings: List[Dict[str, Any]],
        instance_id: Optional[str] = None,
        metadata_options: Optional[str] = None,
        classic_link_vpc_id: Optional[str] = None,
        classic_link_vpc_security_groups: Optional[str] = None,
    ) -> FakeLaunchConfiguration:
        valid_requests = [
            instance_id is not None,
            image_id is not None and instance_type is not None,
        ]
        if not any(valid_requests):
            raise ValidationError(
                "Valid requests must contain either the InstanceID parameter or both the ImageId and InstanceType parameters."
            )
        if instance_id is not None:
            # TODO: https://docs.aws.amazon.com/autoscaling/ec2/userguide/create-lc-with-instanceID.html
            pass
        launch_configuration = FakeLaunchConfiguration(
            name=name,
            image_id=image_id,
            key_name=key_name,
            kernel_id=kernel_id,
            ramdisk_id=ramdisk_id,
            security_groups=security_groups,
            user_data=user_data,
            instance_type=instance_type,
            instance_monitoring=instance_monitoring,
            instance_profile_name=instance_profile_name,
            spot_price=spot_price,
            ebs_optimized=ebs_optimized,
            associate_public_ip_address=associate_public_ip_address,
            block_device_mapping_dict=block_device_mappings,
            account_id=self.account_id,
            region_name=self.region_name,
            metadata_options=metadata_options,
            classic_link_vpc_id=classic_link_vpc_id,
            classic_link_vpc_security_groups=classic_link_vpc_security_groups,
        )
        self.launch_configurations[name] = launch_configuration
        return launch_configuration

    def describe_launch_configurations(
        self, names: Optional[List[str]]
    ) -> List[FakeLaunchConfiguration]:
        configurations = self.launch_configurations.values()
        if names:
            return [
                configuration
                for configuration in configurations
                if configuration.name in names
            ]
        else:
            return list(configurations)

    def delete_launch_configuration(self, launch_configuration_name: str) -> None:
        self.launch_configurations.pop(launch_configuration_name, None)

    def make_int(self, value: Union[None, str, int]) -> Optional[int]:
        return int(value) if value is not None else value

    def put_scheduled_update_group_action(
        self,
        name: str,
        desired_capacity: Union[None, str, int],
        max_size: Union[None, str, int],
        min_size: Union[None, str, int],
        scheduled_action_name: str,
        start_time: str,
        end_time: str,
        recurrence: str,
    ) -> FakeScheduledAction:
        max_size = self.make_int(max_size)
        min_size = self.make_int(min_size)
        desired_capacity = self.make_int(desired_capacity)

        scheduled_action = FakeScheduledAction(
            name=name,
            desired_capacity=desired_capacity,
            max_size=max_size,
            min_size=min_size,
            scheduled_action_name=scheduled_action_name,
            start_time=start_time,
            end_time=end_time,
            recurrence=recurrence,
        )

        self.scheduled_actions[scheduled_action_name] = scheduled_action
        return scheduled_action

    def describe_scheduled_actions(
        self,
        autoscaling_group_name: Optional[str] = None,
        scheduled_action_names: Optional[List[str]] = None,
    ) -> List[FakeScheduledAction]:
        scheduled_actions = []
        for scheduled_action in self.scheduled_actions.values():
            if (
                not autoscaling_group_name
                or scheduled_action.name == autoscaling_group_name
            ):
                if (
                    not scheduled_action_names
                    or scheduled_action.scheduled_action_name in scheduled_action_names
                ):
                    scheduled_actions.append(scheduled_action)

        return scheduled_actions

    def delete_scheduled_action(
        self, auto_scaling_group_name: str, scheduled_action_name: str
    ) -> None:
        scheduled_action = self.describe_scheduled_actions(
            auto_scaling_group_name, [scheduled_action_name]
        )
        if scheduled_action:
            self.scheduled_actions.pop(scheduled_action_name, None)

    def create_auto_scaling_group(
        self,
        name: str,
        availability_zones: List[str],
        desired_capacity: Union[None, str, int],
        max_size: Union[None, str, int],
        min_size: Union[None, str, int],
        launch_config_name: str,
        launch_template: Dict[str, Any],
        vpc_zone_identifier: str,
        default_cooldown: Optional[int],
        health_check_period: Union[None, str, int],
        health_check_type: Optional[str],
        load_balancers: List[str],
        target_group_arns: List[str],
        placement_group: str,
        termination_policies: str,
        tags: List[Dict[str, str]],
        capacity_rebalance: bool = False,
        new_instances_protected_from_scale_in: bool = False,
        instance_id: Optional[str] = None,
        mixed_instance_policy: Optional[Dict[str, Any]] = None,
    ) -> FakeAutoScalingGroup:
        max_size = self.make_int(max_size)
        min_size = self.make_int(min_size)
        desired_capacity = self.make_int(desired_capacity)
        default_cooldown = self.make_int(default_cooldown)

        # Verify only a single launch config-like parameter is provided.
        params = [
            launch_config_name,
            launch_template,
            instance_id,
            mixed_instance_policy,
        ]
        num_params = sum([1 for param in params if param])

        if num_params != 1:
            raise ValidationError(
                "Valid requests must contain either LaunchTemplate, LaunchConfigurationName, "
                "InstanceId or MixedInstancesPolicy parameter."
            )

        if instance_id:
            try:
                instance = self.ec2_backend.get_instance(instance_id)
                launch_config_name = name
                FakeLaunchConfiguration.create_from_instance(
                    launch_config_name, instance, self
                )
            except InvalidInstanceIdError:
                raise InvalidInstanceError(instance_id)

        group = FakeAutoScalingGroup(
            name=name,
            availability_zones=availability_zones,
            desired_capacity=desired_capacity,
            max_size=max_size,
            min_size=min_size,
            launch_config_name=launch_config_name,
            launch_template=launch_template,
            vpc_zone_identifier=vpc_zone_identifier,
            default_cooldown=default_cooldown,
            health_check_period=self.make_int(health_check_period)
            if health_check_period
            else 300,
            health_check_type=health_check_type,
            load_balancers=load_balancers,
            target_group_arns=target_group_arns,
            placement_group=placement_group,
            termination_policies=termination_policies,
            autoscaling_backend=self,
            ec2_backend=self.ec2_backend,
            tags=tags,
            new_instances_protected_from_scale_in=new_instances_protected_from_scale_in,
            mixed_instance_policy=mixed_instance_policy,
            capacity_rebalance=capacity_rebalance,
        )

        self.autoscaling_groups[name] = group
        self.update_attached_elbs(group.name)
        self.update_attached_target_groups(group.name)
        return group

    def update_auto_scaling_group(
        self,
        name: str,
        availability_zones: List[str],
        desired_capacity: Optional[int],
        max_size: Optional[int],
        min_size: Optional[int],
        launch_config_name: str,
        launch_template: Dict[str, Any],
        vpc_zone_identifier: str,
        health_check_period: int,
        health_check_type: str,
        new_instances_protected_from_scale_in: Optional[bool] = None,
    ) -> FakeAutoScalingGroup:
        """
        The parameter DefaultCooldown, PlacementGroup, TerminationPolicies are not yet implemented
        """
        # TODO: Add MixedInstancesPolicy once implemented.
        # Verify only a single launch config-like parameter is provided.
        if launch_config_name and launch_template:
            raise ValidationError(
                "Valid requests must contain either LaunchTemplate, LaunchConfigurationName "
                "or MixedInstancesPolicy parameter."
            )

        group = self.autoscaling_groups[name]
        group.update(
            availability_zones=availability_zones,
            desired_capacity=desired_capacity,
            max_size=max_size,
            min_size=min_size,
            launch_config_name=launch_config_name,
            launch_template=launch_template,
            vpc_zone_identifier=vpc_zone_identifier,
            health_check_period=health_check_period,
            health_check_type=health_check_type,
            new_instances_protected_from_scale_in=new_instances_protected_from_scale_in,
        )
        return group

    def describe_auto_scaling_groups(
        self, names: List[str]
    ) -> List[FakeAutoScalingGroup]:
        groups = self.autoscaling_groups.values()
        if names:
            return [group for group in groups if group.name in names]
        else:
            return list(groups)

    def delete_auto_scaling_group(self, group_name: str) -> None:
        self.set_desired_capacity(group_name, 0)
        self.autoscaling_groups.pop(group_name, None)

    def describe_auto_scaling_instances(
        self, instance_ids: List[str]
    ) -> List[InstanceState]:
        instance_states = []
        for group in self.autoscaling_groups.values():
            instance_states.extend(
                [
                    x
                    for x in group.instance_states
                    if not instance_ids or x.instance.id in instance_ids
                ]
            )
        return instance_states

    def attach_instances(self, group_name: str, instance_ids: List[str]) -> None:
        group = self.autoscaling_groups[group_name]
        original_size = len(group.instance_states)

        if (original_size + len(instance_ids)) > group.max_size:  # type: ignore[operator]
            raise ResourceContentionError
        else:
            group.desired_capacity = original_size + len(instance_ids)
            new_instances = [
                InstanceState(
                    self.ec2_backend.get_instance(x),
                    protected_from_scale_in=group.new_instances_protected_from_scale_in,
                    autoscaling_group=group,
                )
                for x in instance_ids
            ]
            for instance in new_instances:
                self.ec2_backend.create_tags(
                    [instance.instance.id], {ASG_NAME_TAG: group.name}
                )
            group.instance_states.extend(new_instances)
            self.update_attached_elbs(group.name)
            self.update_attached_target_groups(group.name)

    def set_instance_health(self, instance_id: str, health_status: str) -> None:
        """
        The ShouldRespectGracePeriod-parameter is not yet implemented
        """
        instance = self.ec2_backend.get_instance(instance_id)
        instance_state = next(
            instance_state
            for group in self.autoscaling_groups.values()
            for instance_state in group.instance_states
            if instance_state.instance.id == instance.id
        )
        instance_state.health_status = health_status

    def detach_instances(
        self, group_name: str, instance_ids: List[str], should_decrement: bool
    ) -> List[InstanceState]:
        group = self.autoscaling_groups[group_name]
        original_size = group.desired_capacity

        detached_instances = [
            x for x in group.instance_states if x.instance.id in instance_ids
        ]
        for instance in detached_instances:
            self.ec2_backend.delete_tags(
                [instance.instance.id], {ASG_NAME_TAG: group.name}
            )

        new_instance_state = [
            x for x in group.instance_states if x.instance.id not in instance_ids
        ]
        group.instance_states = new_instance_state

        if should_decrement:
            group.desired_capacity = original_size - len(instance_ids)  # type: ignore[operator]

        group.set_desired_capacity(group.desired_capacity)
        return detached_instances

    def set_desired_capacity(
        self, group_name: str, desired_capacity: Optional[int]
    ) -> None:
        group = self.autoscaling_groups[group_name]
        group.set_desired_capacity(desired_capacity)
        self.update_attached_elbs(group_name)

    def change_capacity(
        self, group_name: str, scaling_adjustment: Optional[int]
    ) -> None:
        group = self.autoscaling_groups[group_name]
        desired_capacity = group.desired_capacity + scaling_adjustment  # type: ignore[operator]
        self.set_desired_capacity(group_name, desired_capacity)

    def change_capacity_percent(
        self, group_name: str, scaling_adjustment: Optional[int]
    ) -> None:
        """http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
        If PercentChangeInCapacity returns a value between 0 and 1,
        Auto Scaling will round it off to 1. If the PercentChangeInCapacity
        returns a value greater than 1, Auto Scaling will round it off to the
        lower value. For example, if PercentChangeInCapacity returns 12.5,
        then Auto Scaling will round it off to 12."""
        group = self.autoscaling_groups[group_name]
        percent_change = 1 + (scaling_adjustment / 100.0)  # type: ignore[operator]
        desired_capacity = group.desired_capacity * percent_change  # type: ignore[operator]
        if group.desired_capacity < desired_capacity < group.desired_capacity + 1:  # type: ignore[operator]
            desired_capacity = group.desired_capacity + 1  # type: ignore[operator]
        else:
            desired_capacity = int(desired_capacity)
        self.set_desired_capacity(group_name, desired_capacity)

    def create_lifecycle_hook(
        self,
        name: str,
        as_name: str,
        transition: str,
        timeout: Optional[int],
        result: str,
    ) -> FakeLifeCycleHook:
        lifecycle_hook = FakeLifeCycleHook(name, as_name, transition, timeout, result)

        self.lifecycle_hooks["%s_%s" % (as_name, name)] = lifecycle_hook
        return lifecycle_hook

    def describe_lifecycle_hooks(
        self, as_name: str, lifecycle_hook_names: Optional[str] = None
    ) -> List[FakeLifeCycleHook]:
        return [
            lifecycle_hook
            for lifecycle_hook in self.lifecycle_hooks.values()
            if (lifecycle_hook.as_name == as_name)
            and (
                not lifecycle_hook_names or lifecycle_hook.name in lifecycle_hook_names
            )
        ]

    def delete_lifecycle_hook(self, as_name: str, name: str) -> None:
        self.lifecycle_hooks.pop("%s_%s" % (as_name, name), None)

    def put_scaling_policy(
        self,
        name: str,
        policy_type: str,
        metric_aggregation_type: str,
        adjustment_type: str,
        as_name: str,
        min_adjustment_magnitude: str,
        scaling_adjustment: Optional[int],
        cooldown: Optional[int],
        target_tracking_config: str,
        step_adjustments: str,
        estimated_instance_warmup: str,
        predictive_scaling_configuration: str,
    ) -> FakeScalingPolicy:
        policy = FakeScalingPolicy(
            name,
            policy_type,
            metric_aggregation_type,
            adjustment_type=adjustment_type,
            as_name=as_name,
            min_adjustment_magnitude=min_adjustment_magnitude,
            scaling_adjustment=scaling_adjustment,
            cooldown=cooldown,
            target_tracking_config=target_tracking_config,
            step_adjustments=step_adjustments,
            estimated_instance_warmup=estimated_instance_warmup,
            predictive_scaling_configuration=predictive_scaling_configuration,
            autoscaling_backend=self,
        )

        self.policies[name] = policy
        return policy

    def describe_policies(
        self,
        autoscaling_group_name: Optional[str] = None,
        policy_names: Optional[List[str]] = None,
        policy_types: Optional[List[str]] = None,
    ) -> List[FakeScalingPolicy]:
        return [
            policy
            for policy in self.policies.values()
            if (not autoscaling_group_name or policy.as_name == autoscaling_group_name)
            and (not policy_names or policy.name in policy_names)
            and (not policy_types or policy.policy_type in policy_types)
        ]

    def delete_policy(self, group_name: str) -> None:
        self.policies.pop(group_name, None)

    def execute_policy(self, group_name: str) -> None:
        policy = self.policies[group_name]
        policy.execute()

    def update_attached_elbs(self, group_name: str) -> None:
        group = self.autoscaling_groups[group_name]
        group_instance_ids = set(
            state.instance.id for state in group.active_instances()
        )

        # skip this if group.load_balancers is empty
        # otherwise elb_backend.describe_load_balancers returns all available load balancers
        if not group.load_balancers:
            return
        try:
            elbs = self.elb_backend.describe_load_balancers(names=group.load_balancers)
        except LoadBalancerNotFoundError:
            # ELBs can be deleted before their autoscaling group
            return

        for elb in elbs:
            elb_instace_ids = set(elb.instance_ids)
            self.elb_backend.register_instances(
                elb.name, group_instance_ids - elb_instace_ids, from_autoscaling=True
            )
            self.elb_backend.deregister_instances(
                elb.name, elb_instace_ids - group_instance_ids, from_autoscaling=True
            )

    def update_attached_target_groups(self, group_name: str) -> None:
        group = self.autoscaling_groups[group_name]
        group_instance_ids = set(state.instance.id for state in group.instance_states)

        # no action necessary if target_group_arns is empty
        if not group.target_group_arns:
            return

        target_groups = self.elbv2_backend.describe_target_groups(
            target_group_arns=group.target_group_arns,
            load_balancer_arn=None,
            names=None,
        )

        for target_group in target_groups:
            asg_targets = [
                {"id": x, "port": target_group.port} for x in group_instance_ids
            ]
            self.elbv2_backend.register_targets(target_group.arn, (asg_targets))

    def create_or_update_tags(self, tags: List[Dict[str, str]]) -> None:
        for tag in tags:
            group_name = tag["resource_id"]
            group = self.autoscaling_groups[group_name]
            old_tags = group.tags

            new_tags = []
            # if key was in old_tags, update old tag
            for old_tag in old_tags:
                if old_tag["key"] == tag["key"]:
                    new_tags.append(tag)
                else:
                    new_tags.append(old_tag)

            # if key was never in old_tag's add it (create tag)
            if not any(new_tag["key"] == tag["key"] for new_tag in new_tags):
                new_tags.append(tag)

            group.tags = new_tags

    def delete_tags(self, tags: List[Dict[str, str]]) -> None:
        for tag_to_delete in tags:
            group_name = tag_to_delete["resource_id"]
            key_to_delete = tag_to_delete["key"]
            group = self.autoscaling_groups[group_name]
            old_tags = group.tags
            group.tags = [x for x in old_tags if x["key"] != key_to_delete]

    def attach_load_balancers(
        self, group_name: str, load_balancer_names: List[str]
    ) -> None:
        group = self.autoscaling_groups[group_name]
        group.load_balancers.extend(
            [x for x in load_balancer_names if x not in group.load_balancers]
        )
        self.update_attached_elbs(group_name)

    def describe_load_balancers(self, group_name: str) -> List[str]:
        return self.autoscaling_groups[group_name].load_balancers

    def detach_load_balancers(
        self, group_name: str, load_balancer_names: List[str]
    ) -> None:
        group = self.autoscaling_groups[group_name]
        group_instance_ids = set(state.instance.id for state in group.instance_states)
        elbs = self.elb_backend.describe_load_balancers(names=group.load_balancers)
        for elb in elbs:
            self.elb_backend.deregister_instances(
                elb.name, group_instance_ids, from_autoscaling=True
            )
        group.load_balancers = [
            x for x in group.load_balancers if x not in load_balancer_names
        ]

    def attach_load_balancer_target_groups(
        self, group_name: str, target_group_arns: List[str]
    ) -> None:
        group = self.autoscaling_groups[group_name]
        group.append_target_groups(target_group_arns)
        self.update_attached_target_groups(group_name)

    def describe_load_balancer_target_groups(self, group_name: str) -> List[str]:
        return self.autoscaling_groups[group_name].target_group_arns

    def detach_load_balancer_target_groups(
        self, group_name: str, target_group_arns: List[str]
    ) -> None:
        group = self.autoscaling_groups[group_name]
        group.target_group_arns = [
            x for x in group.target_group_arns if x not in target_group_arns
        ]
        for target_group in target_group_arns:
            asg_targets = [{"id": x.instance.id} for x in group.instance_states]
            self.elbv2_backend.deregister_targets(target_group, (asg_targets))

    def suspend_processes(self, group_name: str, scaling_processes: List[str]) -> None:
        all_proc_names = [
            "Launch",
            "Terminate",
            "AddToLoadBalancer",
            "AlarmNotification",
            "AZRebalance",
            "HealthCheck",
            "InstanceRefresh",
            "ReplaceUnhealthy",
            "ScheduledActions",
        ]
        group = self.autoscaling_groups[group_name]
        set_to_add = set(scaling_processes or all_proc_names)
        group.suspended_processes = list(
            set(group.suspended_processes).union(set_to_add)
        )

    def resume_processes(self, group_name: str, scaling_processes: List[str]) -> None:
        group = self.autoscaling_groups[group_name]
        if scaling_processes:
            group.suspended_processes = list(
                set(group.suspended_processes).difference(set(scaling_processes))
            )
        else:
            group.suspended_processes = []

    def set_instance_protection(
        self,
        group_name: str,
        instance_ids: List[str],
        protected_from_scale_in: Optional[bool],
    ) -> None:
        group = self.autoscaling_groups[group_name]
        protected_instances = [
            x for x in group.instance_states if x.instance.id in instance_ids
        ]
        for instance in protected_instances:
            instance.protected_from_scale_in = protected_from_scale_in

    def notify_terminate_instances(self, instance_ids: List[str]) -> None:
        for (
            autoscaling_group_name,
            autoscaling_group,
        ) in self.autoscaling_groups.items():
            original_active_instance_count = len(autoscaling_group.active_instances())
            autoscaling_group.instance_states = list(
                filter(
                    lambda i_state: i_state.instance.id not in instance_ids,
                    autoscaling_group.instance_states,
                )
            )
            difference = original_active_instance_count - len(
                autoscaling_group.active_instances()
            )
            if difference > 0:
                autoscaling_group.replace_autoscaling_group_instances(
                    difference, autoscaling_group.get_propagated_tags()
                )
                self.update_attached_elbs(autoscaling_group_name)

    def enter_standby_instances(
        self, group_name: str, instance_ids: List[str], should_decrement: bool
    ) -> Tuple[List[InstanceState], Optional[int], Optional[int]]:
        group = self.autoscaling_groups[group_name]
        original_size = group.desired_capacity
        standby_instances = []
        for instance_state in group.instance_states:
            if instance_state.instance.id in instance_ids:
                instance_state.lifecycle_state = "Standby"
                standby_instances.append(instance_state)
        if should_decrement:
            group.desired_capacity = group.desired_capacity - len(instance_ids)  # type: ignore[operator]
        group.set_desired_capacity(group.desired_capacity)
        return standby_instances, original_size, group.desired_capacity

    def exit_standby_instances(
        self, group_name: str, instance_ids: List[str]
    ) -> Tuple[List[InstanceState], Optional[int], int]:
        group = self.autoscaling_groups[group_name]
        original_size = group.desired_capacity
        standby_instances = []
        for instance_state in group.instance_states:
            if instance_state.instance.id in instance_ids:
                instance_state.lifecycle_state = "InService"
                standby_instances.append(instance_state)
        group.desired_capacity = group.desired_capacity + len(instance_ids)  # type: ignore[operator]
        group.set_desired_capacity(group.desired_capacity)
        return standby_instances, original_size, group.desired_capacity

    def terminate_instance(
        self, instance_id: str, should_decrement: bool
    ) -> Tuple[InstanceState, Any, Any]:
        instance = self.ec2_backend.get_instance(instance_id)
        instance_state = next(
            instance_state
            for group in self.autoscaling_groups.values()
            for instance_state in group.instance_states
            if instance_state.instance.id == instance.id
        )
        group = instance.autoscaling_group  # type: ignore[attr-defined]
        original_size = group.desired_capacity
        self.detach_instances(group.name, [instance.id], should_decrement)
        self.ec2_backend.terminate_instances([instance.id])
        return instance_state, original_size, group.desired_capacity

    def describe_tags(self, filters: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Pagination is not yet implemented.
        Only the `auto-scaling-group` and `propagate-at-launch` filters are implemented.
        """
        resources = self.autoscaling_groups.values()
        tags = list(itertools.chain(*[r.tags for r in resources]))
        for f in filters:
            if f["Name"] == "auto-scaling-group":
                tags = [t for t in tags if t["resource_id"] in f["Values"]]
            if f["Name"] == "propagate-at-launch":
                values = [v.lower() for v in f["Values"]]
                tags = [
                    t
                    for t in tags
                    if t.get("propagate_at_launch", "").lower() in values
                ]
        return tags

    def enable_metrics_collection(self, group_name: str, metrics: List[str]) -> None:
        group = self.describe_auto_scaling_groups([group_name])[0]
        group.enable_metrics_collection(metrics)


autoscaling_backends = BackendDict(AutoScalingBackend, "autoscaling")
