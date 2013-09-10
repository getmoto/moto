from moto.core import BaseBackend
from moto.ec2 import ec2_backend

# http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/AS_Concepts.html#Cooldown
DEFAULT_COOLDOWN = 300


class FakeScalingPolicy(object):
    def __init__(self, name, adjustment_type, as_name, scaling_adjustment,
                 cooldown):
        self.name = name
        self.adjustment_type = adjustment_type
        self.as_name = as_name
        self.scaling_adjustment = scaling_adjustment
        if cooldown is not None:
            self.cooldown = cooldown
        else:
            self.cooldown = DEFAULT_COOLDOWN

    def execute(self):
        if self.adjustment_type == 'ExactCapacity':
            autoscaling_backend.set_desired_capacity(self.as_name, self.scaling_adjustment)
        elif self.adjustment_type == 'ChangeInCapacity':
            autoscaling_backend.change_capacity(self.as_name, self.scaling_adjustment)
        elif self.adjustment_type == 'PercentChangeInCapacity':
            autoscaling_backend.change_capacity_percent(self.as_name, self.scaling_adjustment)


class FakeLaunchConfiguration(object):
    def __init__(self, name, image_id, key_name, security_groups, user_data,
                 instance_type, instance_monitoring, instance_profile_name,
                 spot_price, ebs_optimized):
        self.name = name
        self.image_id = image_id
        self.key_name = key_name
        self.security_groups = security_groups
        self.user_data = user_data
        self.instance_type = instance_type
        self.instance_monitoring = instance_monitoring
        self.instance_profile_name = instance_profile_name
        self.spot_price = spot_price
        self.ebs_optimized = ebs_optimized

    @property
    def instance_monitoring_enabled(self):
        if self.instance_monitoring:
            return 'true'
        return 'false'


class FakeAutoScalingGroup(object):
    def __init__(self, name, availability_zones, desired_capacity, max_size,
                 min_size, launch_config_name, vpc_zone_identifier,
                 default_cooldown, health_check_period, health_check_type,
                 load_balancers, placement_group, termination_policies):
        self.name = name
        self.availability_zones = availability_zones
        self.max_size = max_size
        self.min_size = min_size

        self.launch_config = autoscaling_backend.launch_configurations[launch_config_name]
        self.launch_config_name = launch_config_name
        self.vpc_zone_identifier = vpc_zone_identifier

        self.default_cooldown = default_cooldown if default_cooldown else DEFAULT_COOLDOWN
        self.health_check_period = health_check_period
        self.health_check_type = health_check_type if health_check_type else "EC2"
        self.load_balancers = load_balancers
        self.placement_group = placement_group
        self.termination_policies = termination_policies

        self.instances = []
        self.set_desired_capacity(desired_capacity)

    def update(self, availability_zones, desired_capacity, max_size, min_size,
               launch_config_name, vpc_zone_identifier, default_cooldown,
               health_check_period, health_check_type, load_balancers,
               placement_group, termination_policies):
        self.availability_zones = availability_zones
        self.max_size = max_size
        self.min_size = min_size

        self.launch_config = autoscaling_backend.launch_configurations[launch_config_name]
        self.launch_config_name = launch_config_name
        self.vpc_zone_identifier = vpc_zone_identifier

        self.set_desired_capacity(desired_capacity)

    def set_desired_capacity(self, new_capacity):
        if new_capacity is None:
            self.desired_capacity = self.min_size
        else:
            self.desired_capacity = new_capacity

        curr_instance_count = len(self.instances)

        if self.desired_capacity == curr_instance_count:
            return

        if self.desired_capacity > curr_instance_count:
            # Need more instances
            count_needed = self.desired_capacity - curr_instance_count
            reservation = ec2_backend.add_instances(
                self.launch_config.image_id,
                count_needed,
                self.launch_config.user_data
            )
            for instance in reservation.instances:
                instance.autoscaling_group = self
            self.instances.extend(reservation.instances)
        else:
            # Need to remove some instances
            count_to_remove = curr_instance_count - self.desired_capacity
            instances_to_remove = self.instances[:count_to_remove]
            instance_ids_to_remove = [instance.id for instance in instances_to_remove]
            ec2_backend.terminate_instances(instance_ids_to_remove)
            self.instances = self.instances[count_to_remove:]


class AutoScalingBackend(BaseBackend):

    def __init__(self):
        self.autoscaling_groups = {}
        self.launch_configurations = {}
        self.policies = {}

    def create_launch_configuration(self, name, image_id, key_name,
                                    security_groups, user_data, instance_type,
                                    instance_monitoring, instance_profile_name,
                                    spot_price, ebs_optimized):
        launch_configuration = FakeLaunchConfiguration(
            name=name,
            image_id=image_id,
            key_name=key_name,
            security_groups=security_groups,
            user_data=user_data,
            instance_type=instance_type,
            instance_monitoring=instance_monitoring,
            instance_profile_name=instance_profile_name,
            spot_price=spot_price,
            ebs_optimized=ebs_optimized,
        )
        self.launch_configurations[name] = launch_configuration
        return launch_configuration

    def describe_launch_configurations(self, names):
        configurations = self.launch_configurations.values()
        if names:
            return [configuration for configuration in configurations if configuration.name in names]
        else:
            return configurations

    def delete_launch_configuration(self, launch_configuration_name):
        self.launch_configurations.pop(launch_configuration_name, None)

    def create_autoscaling_group(self, name, availability_zones,
                                 desired_capacity, max_size, min_size,
                                 launch_config_name, vpc_zone_identifier,
                                 default_cooldown, health_check_period,
                                 health_check_type, load_balancers,
                                 placement_group, termination_policies):
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
            placement_group=placement_group,
            termination_policies=termination_policies,
        )
        self.autoscaling_groups[name] = group
        return group

    def update_autoscaling_group(self, name, availability_zones,
                                 desired_capacity, max_size, min_size,
                                 launch_config_name, vpc_zone_identifier,
                                 default_cooldown, health_check_period,
                                 health_check_type, load_balancers,
                                 placement_group, termination_policies):
        group = self.autoscaling_groups[name]
        group.update(availability_zones, desired_capacity, max_size,
                     min_size, launch_config_name, vpc_zone_identifier,
                     default_cooldown, health_check_period, health_check_type,
                     load_balancers, placement_group, termination_policies)
        return group

    def describe_autoscaling_groups(self, names):
        groups = self.autoscaling_groups.values()
        if names:
            return [group for group in groups if group.name in names]
        else:
            return groups

    def delete_autoscaling_group(self, group_name):
        self.autoscaling_groups.pop(group_name, None)

    def describe_autoscaling_instances(self):
        instances = []
        for group in self.autoscaling_groups.values():
            instances.extend(group.instances)
        return instances

    def set_desired_capacity(self, group_name, desired_capacity):
        group = self.autoscaling_groups[group_name]
        group.set_desired_capacity(desired_capacity)

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

    def create_autoscaling_policy(self, name, adjustment_type, as_name,
                                  scaling_adjustment, cooldown):
        policy = FakeScalingPolicy(name, adjustment_type, as_name,
                                   scaling_adjustment, cooldown)

        self.policies[name] = policy
        return policy

    def describe_policies(self):
        return self.policies.values()

    def delete_policy(self, group_name):
        self.policies.pop(group_name, None)

    def execute_policy(self, group_name):
        policy = self.policies[group_name]
        policy.execute()

autoscaling_backend = AutoScalingBackend()
