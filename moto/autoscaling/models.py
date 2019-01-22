from __future__ import unicode_literals

import random

from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends
from moto.elb import elb_backends
from moto.elbv2 import elbv2_backends
from moto.elb.exceptions import LoadBalancerNotFoundError
from .exceptions import (
    AutoscalingClientError, ResourceContentionError,
)

# http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/AS_Concepts.html#Cooldown
DEFAULT_COOLDOWN = 300

ASG_NAME_TAG = "aws:autoscaling:groupName"


class InstanceState(object):
    def __init__(self, instance, lifecycle_state="InService",
                 health_status="Healthy", protected_from_scale_in=False):
        self.instance = instance
        self.lifecycle_state = lifecycle_state
        self.health_status = health_status
        self.protected_from_scale_in = protected_from_scale_in


class FakeScalingPolicy(BaseModel):
    def __init__(self, name, policy_type, adjustment_type, as_name, scaling_adjustment,
                 cooldown, autoscaling_backend):
        self.name = name
        self.policy_type = policy_type
        self.adjustment_type = adjustment_type
        self.as_name = as_name
        self.scaling_adjustment = scaling_adjustment
        if cooldown is not None:
            self.cooldown = cooldown
        else:
            self.cooldown = DEFAULT_COOLDOWN
        self.autoscaling_backend = autoscaling_backend

    def execute(self):
        if self.adjustment_type == 'ExactCapacity':
            self.autoscaling_backend.set_desired_capacity(
                self.as_name, self.scaling_adjustment)
        elif self.adjustment_type == 'ChangeInCapacity':
            self.autoscaling_backend.change_capacity(
                self.as_name, self.scaling_adjustment)
        elif self.adjustment_type == 'PercentChangeInCapacity':
            self.autoscaling_backend.change_capacity_percent(
                self.as_name, self.scaling_adjustment)


class FakeLaunchConfiguration(BaseModel):
    def __init__(self, name, image_id, key_name, ramdisk_id, kernel_id, security_groups, user_data,
                 instance_type, instance_monitoring, instance_profile_name,
                 spot_price, ebs_optimized, associate_public_ip_address, block_device_mapping_dict):
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

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

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
            associate_public_ip_address=properties.get(
                "AssociatePublicIpAddress"),
            block_device_mappings=properties.get("BlockDeviceMapping.member")
        )
        return config

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, region_name)
        return cls.create_from_cloudformation_json(new_resource_name, cloudformation_json, region_name)

    @classmethod
    def delete_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
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
            return 'true'
        return 'false'

    def _parse_block_device_mappings(self):
        block_device_map = BlockDeviceMapping()
        for mapping in self.block_device_mapping_dict:
            block_type = BlockDeviceType()
            mount_point = mapping.get('device_name')
            if 'ephemeral' in mapping.get('virtual_name', ''):
                block_type.ephemeral_name = mapping.get('virtual_name')
            else:
                block_type.volume_type = mapping.get('ebs._volume_type')
                block_type.snapshot_id = mapping.get('ebs._snapshot_id')
                block_type.delete_on_termination = mapping.get(
                    'ebs._delete_on_termination')
                block_type.size = mapping.get('ebs._volume_size')
                block_type.iops = mapping.get('ebs._iops')
            block_device_map[mount_point] = block_type
        return block_device_map


class FakeAutoScalingGroup(BaseModel):
    def __init__(self, name, availability_zones, desired_capacity, max_size,
                 min_size, launch_config_name, vpc_zone_identifier,
                 default_cooldown, health_check_period, health_check_type,
                 load_balancers, target_group_arns, placement_group, termination_policies,
                 autoscaling_backend, tags,
                 new_instances_protected_from_scale_in=False):
        self.autoscaling_backend = autoscaling_backend
        self.name = name

        self._set_azs_and_vpcs(availability_zones, vpc_zone_identifier)

        self.max_size = max_size
        self.min_size = min_size

        self.launch_config = self.autoscaling_backend.launch_configurations[
            launch_config_name]
        self.launch_config_name = launch_config_name

        self.default_cooldown = default_cooldown if default_cooldown else DEFAULT_COOLDOWN
        self.health_check_period = health_check_period
        self.health_check_type = health_check_type if health_check_type else "EC2"
        self.load_balancers = load_balancers
        self.target_group_arns = target_group_arns
        self.placement_group = placement_group
        self.termination_policies = termination_policies
        self.new_instances_protected_from_scale_in = new_instances_protected_from_scale_in

        self.suspended_processes = []
        self.instance_states = []
        self.tags = tags if tags else []
        self.set_desired_capacity(desired_capacity)

    def _set_azs_and_vpcs(self, availability_zones, vpc_zone_identifier, update=False):
        # for updates, if only AZs are provided, they must not clash with
        # the AZs of existing VPCs
        if update and availability_zones and not vpc_zone_identifier:
            vpc_zone_identifier = self.vpc_zone_identifier

        if vpc_zone_identifier:
            # extract azs for vpcs
            subnet_ids = vpc_zone_identifier.split(',')
            subnets = self.autoscaling_backend.ec2_backend.get_all_subnets(subnet_ids=subnet_ids)
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
                    "At least one Availability Zone or VPC Subnet is required."
                )
            return

        self.availability_zones = availability_zones
        self.vpc_zone_identifier = vpc_zone_identifier

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        properties = cloudformation_json['Properties']

        launch_config_name = properties.get("LaunchConfigurationName")
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
            vpc_zone_identifier=(
                ','.join(properties.get("VPCZoneIdentifier", [])) or None),
            default_cooldown=properties.get("Cooldown"),
            health_check_period=properties.get("HealthCheckGracePeriod"),
            health_check_type=properties.get("HealthCheckType"),
            load_balancers=load_balancer_names,
            target_group_arns=target_group_arns,
            placement_group=None,
            termination_policies=properties.get("TerminationPolicies", []),
            tags=properties.get("Tags", []),
            new_instances_protected_from_scale_in=properties.get(
                "NewInstancesProtectedFromScaleIn", False)
        )
        return group

    @classmethod
    def update_from_cloudformation_json(cls, original_resource, new_resource_name, cloudformation_json, region_name):
        cls.delete_from_cloudformation_json(
            original_resource.name, cloudformation_json, region_name)
        return cls.create_from_cloudformation_json(new_resource_name, cloudformation_json, region_name)

    @classmethod
    def delete_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
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

    def update(self, availability_zones, desired_capacity, max_size, min_size,
               launch_config_name, vpc_zone_identifier, default_cooldown,
               health_check_period, health_check_type,
               placement_group, termination_policies,
               new_instances_protected_from_scale_in=None):
        self._set_azs_and_vpcs(availability_zones, vpc_zone_identifier, update=True)

        if max_size is not None:
            self.max_size = max_size
        if min_size is not None:
            self.min_size = min_size

        if launch_config_name:
            self.launch_config = self.autoscaling_backend.launch_configurations[
                launch_config_name]
            self.launch_config_name = launch_config_name
        if health_check_period is not None:
            self.health_check_period = health_check_period
        if health_check_type is not None:
            self.health_check_type = health_check_type
        if new_instances_protected_from_scale_in is not None:
            self.new_instances_protected_from_scale_in = new_instances_protected_from_scale_in

        if desired_capacity is not None:
            self.set_desired_capacity(desired_capacity)

    def set_desired_capacity(self, new_capacity):
        if new_capacity is None:
            self.desired_capacity = self.min_size
        else:
            self.desired_capacity = new_capacity

        curr_instance_count = len(self.instance_states)

        if self.desired_capacity == curr_instance_count:
            return

        if self.desired_capacity > curr_instance_count:
            # Need more instances
            count_needed = int(self.desired_capacity) - int(curr_instance_count)

            propagated_tags = self.get_propagated_tags()
            self.replace_autoscaling_group_instances(count_needed, propagated_tags)
        else:
            # Need to remove some instances
            count_to_remove = curr_instance_count - self.desired_capacity
            instances_to_remove = [  # only remove unprotected
                state for state in self.instance_states
                if not state.protected_from_scale_in
            ][:count_to_remove]
            if instances_to_remove:  # just in case not instances to remove
                instance_ids_to_remove = [
                    instance.instance.id for instance in instances_to_remove]
                self.autoscaling_backend.ec2_backend.terminate_instances(
                    instance_ids_to_remove)
                self.instance_states = list(set(self.instance_states) - set(instances_to_remove))

    def get_propagated_tags(self):
        propagated_tags = {}
        for tag in self.tags:
            # boto uses 'propagate_at_launch
            # boto3 and cloudformation use PropagateAtLaunch
            if 'propagate_at_launch' in tag and tag['propagate_at_launch'] == 'true':
                propagated_tags[tag['key']] = tag['value']
            if 'PropagateAtLaunch' in tag and tag['PropagateAtLaunch']:
                propagated_tags[tag['Key']] = tag['Value']
        return propagated_tags

    def replace_autoscaling_group_instances(self, count_needed, propagated_tags):
        propagated_tags[ASG_NAME_TAG] = self.name
        reservation = self.autoscaling_backend.ec2_backend.add_instances(
            self.launch_config.image_id,
            count_needed,
            self.launch_config.user_data,
            self.launch_config.security_groups,
            instance_type=self.launch_config.instance_type,
            tags={'instance': propagated_tags},
            placement=random.choice(self.availability_zones),
        )
        for instance in reservation.instances:
            instance.autoscaling_group = self
            self.instance_states.append(InstanceState(
                instance,
                protected_from_scale_in=self.new_instances_protected_from_scale_in,
            ))

    def append_target_groups(self, target_group_arns):
        append = [x for x in target_group_arns if x not in self.target_group_arns]
        self.target_group_arns.extend(append)


class AutoScalingBackend(BaseBackend):
    def __init__(self, ec2_backend, elb_backend, elbv2_backend):
        self.autoscaling_groups = OrderedDict()
        self.launch_configurations = OrderedDict()
        self.policies = {}
        self.ec2_backend = ec2_backend
        self.elb_backend = elb_backend
        self.elbv2_backend = elbv2_backend

    def reset(self):
        ec2_backend = self.ec2_backend
        elb_backend = self.elb_backend
        elbv2_backend = self.elbv2_backend
        self.__dict__ = {}
        self.__init__(ec2_backend, elb_backend, elbv2_backend)

    def create_launch_configuration(self, name, image_id, key_name, kernel_id, ramdisk_id,
                                    security_groups, user_data, instance_type,
                                    instance_monitoring, instance_profile_name,
                                    spot_price, ebs_optimized, associate_public_ip_address, block_device_mappings):
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
        )
        self.launch_configurations[name] = launch_configuration
        return launch_configuration

    def describe_launch_configurations(self, names):
        configurations = self.launch_configurations.values()
        if names:
            return [configuration for configuration in configurations if configuration.name in names]
        else:
            return list(configurations)

    def delete_launch_configuration(self, launch_configuration_name):
        self.launch_configurations.pop(launch_configuration_name, None)

    def create_auto_scaling_group(self, name, availability_zones,
                                 desired_capacity, max_size, min_size,
                                 launch_config_name, vpc_zone_identifier,
                                 default_cooldown, health_check_period,
                                 health_check_type, load_balancers,
                                 target_group_arns, placement_group,
                                 termination_policies, tags,
                                 new_instances_protected_from_scale_in=False):

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

        group = FakeAutoScalingGroup(
            name=name,
            availability_zones=availability_zones,
            desired_capacity=desired_capacity,
            max_size=max_size,
            min_size=min_size,
            launch_config_name=launch_config_name,
            vpc_zone_identifier=vpc_zone_identifier,
            default_cooldown=default_cooldown,
            health_check_period=health_check_period,
            health_check_type=health_check_type,
            load_balancers=load_balancers,
            target_group_arns=target_group_arns,
            placement_group=placement_group,
            termination_policies=termination_policies,
            autoscaling_backend=self,
            tags=tags,
            new_instances_protected_from_scale_in=new_instances_protected_from_scale_in,
        )

        self.autoscaling_groups[name] = group
        self.update_attached_elbs(group.name)
        self.update_attached_target_groups(group.name)
        return group

    def update_auto_scaling_group(self, name, availability_zones,
                                 desired_capacity, max_size, min_size,
                                 launch_config_name, vpc_zone_identifier,
                                 default_cooldown, health_check_period,
                                 health_check_type, placement_group,
                                 termination_policies,
                                 new_instances_protected_from_scale_in=None):
        group = self.autoscaling_groups[name]
        group.update(availability_zones, desired_capacity, max_size,
                     min_size, launch_config_name, vpc_zone_identifier,
                     default_cooldown, health_check_period, health_check_type,
                     placement_group, termination_policies,
                     new_instances_protected_from_scale_in=new_instances_protected_from_scale_in)
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

    def describe_auto_scaling_instances(self):
        instance_states = []
        for group in self.autoscaling_groups.values():
            instance_states.extend(group.instance_states)
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
                )
                for x in instance_ids
            ]
            for instance in new_instances:
                self.ec2_backend.create_tags([instance.instance.id], {ASG_NAME_TAG: group.name})
            group.instance_states.extend(new_instances)
            self.update_attached_elbs(group.name)

    def set_instance_health(self, instance_id, health_status, should_respect_grace_period):
        instance = self.ec2_backend.get_instance(instance_id)
        instance_state = next(instance_state for group in self.autoscaling_groups.values()
                              for instance_state in group.instance_states if instance_state.instance.id == instance.id)
        instance_state.health_status = health_status

    def detach_instances(self, group_name, instance_ids, should_decrement):
        group = self.autoscaling_groups[group_name]
        original_size = len(group.instance_states)

        detached_instances = [x for x in group.instance_states if x.instance.id in instance_ids]
        for instance in detached_instances:
            self.ec2_backend.delete_tags([instance.instance.id], {ASG_NAME_TAG: group.name})

        new_instance_state = [x for x in group.instance_states if x.instance.id not in instance_ids]
        group.instance_states = new_instance_state

        if should_decrement:
            group.desired_capacity = original_size - len(instance_ids)
        else:
            count_needed = len(instance_ids)
            group.replace_autoscaling_group_instances(count_needed, group.get_propagated_tags())

        self.update_attached_elbs(group_name)
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
        """ http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
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

    def create_autoscaling_policy(self, name, policy_type, adjustment_type, as_name,
                                  scaling_adjustment, cooldown):
        policy = FakeScalingPolicy(name, policy_type, adjustment_type, as_name,
                                   scaling_adjustment, cooldown, self)

        self.policies[name] = policy
        return policy

    def describe_policies(self, autoscaling_group_name=None, policy_names=None, policy_types=None):
        return [policy for policy in self.policies.values()
                if (not autoscaling_group_name or policy.as_name == autoscaling_group_name) and
                (not policy_names or policy.name in policy_names) and
                (not policy_types or policy.policy_type in policy_types)]

    def delete_policy(self, group_name):
        self.policies.pop(group_name, None)

    def execute_policy(self, group_name):
        policy = self.policies[group_name]
        policy.execute()

    def update_attached_elbs(self, group_name):
        group = self.autoscaling_groups[group_name]
        group_instance_ids = set(
            state.instance.id for state in group.instance_states)

        # skip this if group.load_balancers is empty
        # otherwise elb_backend.describe_load_balancers returns all available load balancers
        if not group.load_balancers:
            return
        try:
            elbs = self.elb_backend.describe_load_balancers(
                names=group.load_balancers)
        except LoadBalancerNotFoundError:
            # ELBs can be deleted before their autoscaling group
            return

        for elb in elbs:
            elb_instace_ids = set(elb.instance_ids)
            self.elb_backend.register_instances(
                elb.name, group_instance_ids - elb_instace_ids)
            self.elb_backend.deregister_instances(
                elb.name, elb_instace_ids - group_instance_ids)

    def update_attached_target_groups(self, group_name):
        group = self.autoscaling_groups[group_name]
        group_instance_ids = set(
            state.instance.id for state in group.instance_states)

        # no action necessary if target_group_arns is empty
        if not group.target_group_arns:
            return

        target_groups = self.elbv2_backend.describe_target_groups(
            target_group_arns=group.target_group_arns,
            load_balancer_arn=None,
            names=None)

        for target_group in target_groups:
            asg_targets = [{'id': x, 'port': target_group.port} for x in group_instance_ids]
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
            if not any(new_tag['key'] == tag['key'] for new_tag in new_tags):
                new_tags.append(tag)

            group.tags = new_tags

    def attach_load_balancers(self, group_name, load_balancer_names):
        group = self.autoscaling_groups[group_name]
        group.load_balancers.extend(
            [x for x in load_balancer_names if x not in group.load_balancers])
        self.update_attached_elbs(group_name)

    def describe_load_balancers(self, group_name):
        return self.autoscaling_groups[group_name].load_balancers

    def detach_load_balancers(self, group_name, load_balancer_names):
        group = self.autoscaling_groups[group_name]
        group_instance_ids = set(
            state.instance.id for state in group.instance_states)
        elbs = self.elb_backend.describe_load_balancers(names=group.load_balancers)
        for elb in elbs:
            self.elb_backend.deregister_instances(
                elb.name, group_instance_ids)
        group.load_balancers = [x for x in group.load_balancers if x not in load_balancer_names]

    def attach_load_balancer_target_groups(self, group_name, target_group_arns):
        group = self.autoscaling_groups[group_name]
        group.append_target_groups(target_group_arns)
        self.update_attached_target_groups(group_name)

    def describe_load_balancer_target_groups(self, group_name):
        return self.autoscaling_groups[group_name].target_group_arns

    def detach_load_balancer_target_groups(self, group_name, target_group_arns):
        group = self.autoscaling_groups[group_name]
        group.target_group_arns = [x for x in group.target_group_arns if x not in target_group_arns]
        for target_group in target_group_arns:
            asg_targets = [{'id': x.instance.id} for x in group.instance_states]
            self.elbv2_backend.deregister_targets(target_group, (asg_targets))

    def suspend_processes(self, group_name, scaling_processes):
        group = self.autoscaling_groups[group_name]
        group.suspended_processes = scaling_processes or []

    def set_instance_protection(self, group_name, instance_ids, protected_from_scale_in):
        group = self.autoscaling_groups[group_name]
        protected_instances = [
            x for x in group.instance_states if x.instance.id in instance_ids]
        for instance in protected_instances:
            instance.protected_from_scale_in = protected_from_scale_in


autoscaling_backends = {}
for region, ec2_backend in ec2_backends.items():
    autoscaling_backends[region] = AutoScalingBackend(
        ec2_backend, elb_backends[region], elbv2_backends[region])
