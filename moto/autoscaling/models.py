import itertools
import random
from uuid import uuid4

from moto.packages.boto.ec2.blockdevicemapping import (
    BlockDeviceType,
    BlockDeviceMapping,
)
from moto.ec2.exceptions import InvalidInstanceIdError

from collections import OrderedDict
from moto.core import get_account_id, BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import camelcase_to_underscores, BackendDict
from moto.ec2 import ec2_backends
from moto.elb import elb_backends
from moto.elbv2 import elbv2_backends
from moto.elb.exceptions import LoadBalancerNotFoundError
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
        instance,
        lifecycle_state="InService",
        health_status="Healthy",
        protected_from_scale_in=False,
        autoscaling_group=None,
    ):
        self.instance = instance
        self.lifecycle_state = lifecycle_state
        self.health_status = health_status
        self.protected_from_scale_in = protected_from_scale_in
        if not hasattr(self.instance, "autoscaling_group"):
            self.instance.autoscaling_group = autoscaling_group


class FakeLifeCycleHook(BaseModel):
    def __init__(self, name, as_name, transition, timeout, result):
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
        name,
        policy_type,
        metric_aggregation_type,
        adjustment_type,
        as_name,
        min_adjustment_magnitude,
        scaling_adjustment,
        cooldown,
        target_tracking_config,
        step_adjustments,
        estimated_instance_warmup,
        predictive_scaling_configuration,
        autoscaling_backend,
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
    def arn(self):
        return f"arn:aws:autoscaling:{self.autoscaling_backend.region}:{get_account_id()}:scalingPolicy:c322761b-3172-4d56-9a21-0ed9d6161d67:autoScalingGroupName/{self.as_name}:policyName/{self.name}"

    def execute(self):
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
        name,
        image_id,
        key_name,
        ramdisk_id,
        kernel_id,
        security_groups,
        user_data,
        instance_type,
        instance_monitoring,
        instance_profile_name,
        spot_price,
        ebs_optimized,
        associate_public_ip_address,
        block_device_mapping_dict,
        region_name,
        metadata_options,
        classic_link_vpc_id,
        classic_link_vpc_security_groups,
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
        self.associate_public_ip_address = associate_public_ip_address
        self.block_device_mapping_dict = block_device_mapping_dict
        self.metadata_options = metadata_options
        self.classic_link_vpc_id = classic_link_vpc_id
        self.classic_link_vpc_security_groups = classic_link_vpc_security_groups
        self.arn = f"arn:aws:autoscaling:{region_name}:{get_account_id()}:launchConfiguration:9dbbbf87-6141-428a-a409-0752edbe6cad:launchConfigurationName/{self.name}"

    @classmethod
    def create_from_instance(cls, name, instance, backend):
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
    def cloudformation_name_type():
        return "LaunchConfigurationName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-autoscaling-launchconfiguration.html
        return "AWS::AutoScaling::LaunchConfiguration"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        instance_profile_name = properties.get("IamInstanceProfile")

        backend = autoscaling_backends[region_name]
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
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        backend = autoscaling_backends[region_name]
        try:
            backend.delete_launch_configuration(resource_name)
        except KeyError:
            pass

    def delete(self, region_name):
        backend = autoscaling_backends[region_name]
        backend.delete_launch_configuration(self.name)

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def block_device_mappings(self):
        if not self.block_device_mapping_dict:
            return None
        else:
            return self._parse_block_device_mappings()

    @property
    def instance_monitoring_enabled(self):
        if self.instance_monitoring:
            return "true"
        return "false"

    def _parse_block_device_mappings(self):
        block_device_map = BlockDeviceMapping()
        for mapping in self.block_device_mapping_dict:
            block_type = BlockDeviceType()
            mount_point = mapping.get("DeviceName")
            if mapping.get("VirtualName") and "ephemeral" in mapping.get("VirtualName"):
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


class FakeAutoScalingGroup(CloudFormationModel):
    def __init__(
        self,
        name,
        availability_zones,
        desired_capacity,
        max_size,
        min_size,
        launch_config_name,
        launch_template,
        vpc_zone_identifier,
        default_cooldown,
        health_check_period,
        health_check_type,
        load_balancers,
        target_group_arns,
        placement_group,
        termination_policies,
        autoscaling_backend,
        ec2_backend,
        tags,
        new_instances_protected_from_scale_in=False,
    ):
        self.autoscaling_backend = autoscaling_backend
        self.ec2_backend = ec2_backend
        self.name = name
        self._id = str(uuid4())
        self.region = self.autoscaling_backend.region

        self._set_azs_and_vpcs(availability_zones, vpc_zone_identifier)

        self.max_size = max_size
        self.min_size = min_size

        self.launch_template = None
        self.launch_config = None

        self._set_launch_configuration(launch_config_name, launch_template)

        self.default_cooldown = (
            default_cooldown if default_cooldown else DEFAULT_COOLDOWN
        )
        self.health_check_period = health_check_period
        self.health_check_type = health_check_type if health_check_type else "EC2"
        self.load_balancers = load_balancers
        self.target_group_arns = target_group_arns
        self.placement_group = placement_group
        self.termination_policies = termination_policies
        self.new_instances_protected_from_scale_in = (
            new_instances_protected_from_scale_in
        )

        self.suspended_processes = []
        self.instance_states = []
        self.tags = tags or []
        self.set_desired_capacity(desired_capacity)

    @property
    def tags(self):
        return self._tags

    @tags.setter
    def tags(self, tags):
        for tag in tags:
            if "resource_id" not in tag or not tag["resource_id"]:
                tag["resource_id"] = self.name
            if "resource_type" not in tag or not tag["resource_type"]:
                tag["resource_type"] = "auto-scaling-group"
        self._tags = tags

    @property
    def arn(self):
        return f"arn:aws:autoscaling:{self.region}:{get_account_id()}:autoScalingGroup:{self._id}:autoScalingGroupName/{self.name}"

    def active_instances(self):
        return [x for x in self.instance_states if x.lifecycle_state == "InService"]

    def _set_azs_and_vpcs(self, availability_zones, vpc_zone_identifier, update=False):
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

    def _set_launch_configuration(self, launch_config_name, launch_template):
        if launch_config_name:
            self.launch_config = self.autoscaling_backend.launch_configurations[
                launch_config_name
            ]
            self.launch_config_name = launch_config_name

        if launch_template:
            launch_template_id = launch_template.get("launch_template_id")
            launch_template_name = launch_template.get("launch_template_name")

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
            self.launch_template_version = launch_template["version"]

    @staticmethod
    def __set_string_propagate_at_launch_booleans_on_tags(tags):
        bool_to_string = {True: "true", False: "false"}
        for tag in tags:
            if "PropagateAtLaunch" in tag:
                tag["PropagateAtLaunch"] = bool_to_string[tag["PropagateAtLaunch"]]
        return tags

    @staticmethod
    def cloudformation_name_type():
        return "AutoScalingGroupName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-autoscaling-autoscalinggroup.html
        return "AWS::AutoScaling::AutoScalingGroup"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]

        launch_config_name = properties.get("LaunchConfigurationName")
        launch_template = {
            camelcase_to_underscores(k): v
            for k, v in properties.get("LaunchTemplate", {}).items()
        }
        load_balancer_names = properties.get("LoadBalancerNames", [])
        target_group_arns = properties.get("TargetGroupARNs", [])

        backend = autoscaling_backends[region_name]
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
            tags=cls.__set_string_propagate_at_launch_booleans_on_tags(
                properties.get("Tags", [])
            ),
            new_instances_protected_from_scale_in=properties.get(
                "NewInstancesProtectedFromScaleIn", False
            ),
        )
        return group

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, region_name
        )
        return cls.create_from_cloudformation_json(
            new_resource_name, cloudformation_json, region_name
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        backend = autoscaling_backends[region_name]
        try:
            backend.delete_auto_scaling_group(resource_name)
        except KeyError:
            pass

    def delete(self, region_name):
        backend = autoscaling_backends[region_name]
        backend.delete_auto_scaling_group(self.name)

    @property
    def physical_resource_id(self):
        return self.name

    @property
    def image_id(self):
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.image_id

        return self.launch_config.image_id

    @property
    def instance_type(self):
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.instance_type

        return self.launch_config.instance_type

    @property
    def user_data(self):
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.user_data

        return self.launch_config.user_data

    @property
    def security_groups(self):
        if self.launch_template:
            version = self.launch_template.get_version(self.launch_template_version)
            return version.security_groups

        return self.launch_config.security_groups

    def update(
        self,
        availability_zones,
        desired_capacity,
        max_size,
        min_size,
        launch_config_name,
        launch_template,
        vpc_zone_identifier,
        health_check_period,
        health_check_type,
        new_instances_protected_from_scale_in=None,
    ):
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

        self._set_launch_configuration(launch_config_name, launch_template)

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

    def set_desired_capacity(self, new_capacity):
        if new_capacity is None:
            self.desired_capacity = self.min_size
        else:
            self.desired_capacity = new_capacity

        curr_instance_count = len(self.active_instances())

        if self.desired_capacity == curr_instance_count:
            pass  # Nothing to do here
        elif self.desired_capacity > curr_instance_count:
            # Need more instances
            count_needed = int(self.desired_capacity) - int(curr_instance_count)

            propagated_tags = self.get_propagated_tags()
            self.replace_autoscaling_group_instances(count_needed, propagated_tags)
        else:
            # Need to remove some instances
            count_to_remove = curr_instance_count - self.desired_capacity
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

    def get_propagated_tags(self):
        propagated_tags = {}
        for tag in self.tags:
            # boto uses 'propagate_at_launch
            # boto3 and cloudformation use PropagateAtLaunch
            if "propagate_at_launch" in tag and tag["propagate_at_launch"] == "true":
                propagated_tags[tag["key"]] = tag["value"]
            if "PropagateAtLaunch" in tag and tag["PropagateAtLaunch"] == "true":
                propagated_tags[tag["Key"]] = tag["Value"]
        return propagated_tags

    def replace_autoscaling_group_instances(self, count_needed, propagated_tags):
        propagated_tags[ASG_NAME_TAG] = self.name

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
        )
        for instance in reservation.instances:
            instance.autoscaling_group = self
            self.instance_states.append(
                InstanceState(
                    instance,
                    protected_from_scale_in=self.new_instances_protected_from_scale_in,
                )
            )

    def append_target_groups(self, target_group_arns):
        append = [x for x in target_group_arns if x not in self.target_group_arns]
        self.target_group_arns.extend(append)


class AutoScalingBackend(BaseBackend):
    def __init__(self, region_name):
        self.autoscaling_groups = OrderedDict()
        self.launch_configurations = OrderedDict()
        self.policies = {}
        self.lifecycle_hooks = {}
        self.ec2_backend = ec2_backends[region_name]
        self.elb_backend = elb_backends[region_name]
        self.elbv2_backend = elbv2_backends[region_name]
        self.region = region_name

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "autoscaling"
        ) + BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "autoscaling-plans"
        )

    def create_launch_configuration(
        self,
        name,
        image_id,
        key_name,
        kernel_id,
        ramdisk_id,
        security_groups,
        user_data,
        instance_type,
        instance_monitoring,
        instance_profile_name,
        spot_price,
        ebs_optimized,
        associate_public_ip_address,
        block_device_mappings,
        instance_id=None,
        metadata_options=None,
        classic_link_vpc_id=None,
        classic_link_vpc_security_groups=None,
    ):
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
            region_name=self.region,
            metadata_options=metadata_options,
            classic_link_vpc_id=classic_link_vpc_id,
            classic_link_vpc_security_groups=classic_link_vpc_security_groups,
        )
        self.launch_configurations[name] = launch_configuration
        return launch_configuration

    def describe_launch_configurations(self, names):
        configurations = self.launch_configurations.values()
        if names:
            return [
                configuration
                for configuration in configurations
                if configuration.name in names
            ]
        else:
            return list(configurations)

    def delete_launch_configuration(self, launch_configuration_name):
        self.launch_configurations.pop(launch_configuration_name, None)

    def create_auto_scaling_group(
        self,
        name,
        availability_zones,
        desired_capacity,
        max_size,
        min_size,
        launch_config_name,
        launch_template,
        vpc_zone_identifier,
        default_cooldown,
        health_check_period,
        health_check_type,
        load_balancers,
        target_group_arns,
        placement_group,
        termination_policies,
        tags,
        new_instances_protected_from_scale_in=False,
        instance_id=None,
    ):
        def make_int(value):
            return int(value) if value is not None else value

        max_size = make_int(max_size)
        min_size = make_int(min_size)
        desired_capacity = make_int(desired_capacity)
        default_cooldown = make_int(default_cooldown)
        if health_check_period is None:
            health_check_period = 300
        else:
            health_check_period = make_int(health_check_period)

        # TODO: Add MixedInstancesPolicy once implemented.
        # Verify only a single launch config-like parameter is provided.
        params = [launch_config_name, launch_template, instance_id]
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
            health_check_period=health_check_period,
            health_check_type=health_check_type,
            load_balancers=load_balancers,
            target_group_arns=target_group_arns,
            placement_group=placement_group,
            termination_policies=termination_policies,
            autoscaling_backend=self,
            ec2_backend=self.ec2_backend,
            tags=tags,
            new_instances_protected_from_scale_in=new_instances_protected_from_scale_in,
        )

        self.autoscaling_groups[name] = group
        self.update_attached_elbs(group.name)
        self.update_attached_target_groups(group.name)
        return group

    def update_auto_scaling_group(
        self,
        name,
        availability_zones,
        desired_capacity,
        max_size,
        min_size,
        launch_config_name,
        launch_template,
        vpc_zone_identifier,
        health_check_period,
        health_check_type,
        new_instances_protected_from_scale_in=None,
    ):
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

    def describe_auto_scaling_groups(self, names):
        groups = self.autoscaling_groups.values()
        if names:
            return [group for group in groups if group.name in names]
        else:
            return list(groups)

    def delete_auto_scaling_group(self, group_name):
        self.set_desired_capacity(group_name, 0)
        self.autoscaling_groups.pop(group_name, None)

    def describe_auto_scaling_instances(self, instance_ids):
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

    def attach_instances(self, group_name, instance_ids):
        group = self.autoscaling_groups[group_name]
        original_size = len(group.instance_states)

        if (original_size + len(instance_ids)) > group.max_size:
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

    def set_instance_health(self, instance_id, health_status):
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

    def detach_instances(self, group_name, instance_ids, should_decrement):
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
            group.desired_capacity = original_size - len(instance_ids)

        group.set_desired_capacity(group.desired_capacity)
        return detached_instances

    def set_desired_capacity(self, group_name, desired_capacity):
        group = self.autoscaling_groups[group_name]
        group.set_desired_capacity(desired_capacity)
        self.update_attached_elbs(group_name)

    def change_capacity(self, group_name, scaling_adjustment):
        group = self.autoscaling_groups[group_name]
        desired_capacity = group.desired_capacity + scaling_adjustment
        self.set_desired_capacity(group_name, desired_capacity)

    def change_capacity_percent(self, group_name, scaling_adjustment):
        """http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
        If PercentChangeInCapacity returns a value between 0 and 1,
        Auto Scaling will round it off to 1. If the PercentChangeInCapacity
        returns a value greater than 1, Auto Scaling will round it off to the
        lower value. For example, if PercentChangeInCapacity returns 12.5,
        then Auto Scaling will round it off to 12."""
        group = self.autoscaling_groups[group_name]
        percent_change = 1 + (scaling_adjustment / 100.0)
        desired_capacity = group.desired_capacity * percent_change
        if group.desired_capacity < desired_capacity < group.desired_capacity + 1:
            desired_capacity = group.desired_capacity + 1
        else:
            desired_capacity = int(desired_capacity)
        self.set_desired_capacity(group_name, desired_capacity)

    def create_lifecycle_hook(self, name, as_name, transition, timeout, result):
        lifecycle_hook = FakeLifeCycleHook(name, as_name, transition, timeout, result)

        self.lifecycle_hooks["%s_%s" % (as_name, name)] = lifecycle_hook
        return lifecycle_hook

    def describe_lifecycle_hooks(self, as_name, lifecycle_hook_names=None):
        return [
            lifecycle_hook
            for lifecycle_hook in self.lifecycle_hooks.values()
            if (lifecycle_hook.as_name == as_name)
            and (
                not lifecycle_hook_names or lifecycle_hook.name in lifecycle_hook_names
            )
        ]

    def delete_lifecycle_hook(self, as_name, name):
        self.lifecycle_hooks.pop("%s_%s" % (as_name, name), None)

    def put_scaling_policy(
        self,
        name,
        policy_type,
        metric_aggregation_type,
        adjustment_type,
        as_name,
        min_adjustment_magnitude,
        scaling_adjustment,
        cooldown,
        target_tracking_config,
        step_adjustments,
        estimated_instance_warmup,
        predictive_scaling_configuration,
    ):
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
        self, autoscaling_group_name=None, policy_names=None, policy_types=None
    ):
        return [
            policy
            for policy in self.policies.values()
            if (not autoscaling_group_name or policy.as_name == autoscaling_group_name)
            and (not policy_names or policy.name in policy_names)
            and (not policy_types or policy.policy_type in policy_types)
        ]

    def delete_policy(self, group_name):
        self.policies.pop(group_name, None)

    def execute_policy(self, group_name):
        policy = self.policies[group_name]
        policy.execute()

    def update_attached_elbs(self, group_name):
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

    def update_attached_target_groups(self, group_name):
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

    def create_or_update_tags(self, tags):
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

    def delete_tags(self, tags):
        for tag_to_delete in tags:
            group_name = tag_to_delete["resource_id"]
            key_to_delete = tag_to_delete["key"]
            group = self.autoscaling_groups[group_name]
            old_tags = group.tags
            group.tags = [x for x in old_tags if x["key"] != key_to_delete]

    def attach_load_balancers(self, group_name, load_balancer_names):
        group = self.autoscaling_groups[group_name]
        group.load_balancers.extend(
            [x for x in load_balancer_names if x not in group.load_balancers]
        )
        self.update_attached_elbs(group_name)

    def describe_load_balancers(self, group_name):
        return self.autoscaling_groups[group_name].load_balancers

    def detach_load_balancers(self, group_name, load_balancer_names):
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

    def attach_load_balancer_target_groups(self, group_name, target_group_arns):
        group = self.autoscaling_groups[group_name]
        group.append_target_groups(target_group_arns)
        self.update_attached_target_groups(group_name)

    def describe_load_balancer_target_groups(self, group_name):
        return self.autoscaling_groups[group_name].target_group_arns

    def detach_load_balancer_target_groups(self, group_name, target_group_arns):
        group = self.autoscaling_groups[group_name]
        group.target_group_arns = [
            x for x in group.target_group_arns if x not in target_group_arns
        ]
        for target_group in target_group_arns:
            asg_targets = [{"id": x.instance.id} for x in group.instance_states]
            self.elbv2_backend.deregister_targets(target_group, (asg_targets))

    def suspend_processes(self, group_name, scaling_processes):
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

    def resume_processes(self, group_name, scaling_processes):
        group = self.autoscaling_groups[group_name]
        if scaling_processes:
            group.suspended_processes = list(
                set(group.suspended_processes).difference(set(scaling_processes))
            )
        else:
            group.suspended_processes = []

    def set_instance_protection(
        self, group_name, instance_ids, protected_from_scale_in
    ):
        group = self.autoscaling_groups[group_name]
        protected_instances = [
            x for x in group.instance_states if x.instance.id in instance_ids
        ]
        for instance in protected_instances:
            instance.protected_from_scale_in = protected_from_scale_in

    def notify_terminate_instances(self, instance_ids):
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

    def enter_standby_instances(self, group_name, instance_ids, should_decrement):
        group = self.autoscaling_groups[group_name]
        original_size = group.desired_capacity
        standby_instances = []
        for instance_state in group.instance_states:
            if instance_state.instance.id in instance_ids:
                instance_state.lifecycle_state = "Standby"
                standby_instances.append(instance_state)
        if should_decrement:
            group.desired_capacity = group.desired_capacity - len(instance_ids)
        group.set_desired_capacity(group.desired_capacity)
        return standby_instances, original_size, group.desired_capacity

    def exit_standby_instances(self, group_name, instance_ids):
        group = self.autoscaling_groups[group_name]
        original_size = group.desired_capacity
        standby_instances = []
        for instance_state in group.instance_states:
            if instance_state.instance.id in instance_ids:
                instance_state.lifecycle_state = "InService"
                standby_instances.append(instance_state)
        group.desired_capacity = group.desired_capacity + len(instance_ids)
        group.set_desired_capacity(group.desired_capacity)
        return standby_instances, original_size, group.desired_capacity

    def terminate_instance(self, instance_id, should_decrement):
        instance = self.ec2_backend.get_instance(instance_id)
        instance_state = next(
            instance_state
            for group in self.autoscaling_groups.values()
            for instance_state in group.instance_states
            if instance_state.instance.id == instance.id
        )
        group = instance.autoscaling_group
        original_size = group.desired_capacity
        self.detach_instances(group.name, [instance.id], should_decrement)
        self.ec2_backend.terminate_instances([instance.id])
        return instance_state, original_size, group.desired_capacity

    def describe_tags(self, filters):
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


autoscaling_backends = BackendDict(AutoScalingBackend, "ec2")
