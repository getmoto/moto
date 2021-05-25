from __future__ import unicode_literals
import datetime

from moto.core.responses import BaseResponse
from moto.core.utils import (
    amz_crc32,
    amzn_request_id,
    iso_8601_datetime_with_milliseconds,
)
from .models import autoscaling_backends


class AutoScalingResponse(BaseResponse):
    @property
    def autoscaling_backend(self):
        return autoscaling_backends[self.region]

    def create_launch_configuration(self):
        instance_monitoring_string = self._get_param("InstanceMonitoring.Enabled")
        if instance_monitoring_string == "true":
            instance_monitoring = True
        else:
            instance_monitoring = False
        self.autoscaling_backend.create_launch_configuration(
            name=self._get_param("LaunchConfigurationName"),
            image_id=self._get_param("ImageId"),
            key_name=self._get_param("KeyName"),
            ramdisk_id=self._get_param("RamdiskId"),
            kernel_id=self._get_param("KernelId"),
            security_groups=self._get_multi_param("SecurityGroups.member"),
            user_data=self._get_param("UserData"),
            instance_type=self._get_param("InstanceType"),
            instance_monitoring=instance_monitoring,
            instance_profile_name=self._get_param("IamInstanceProfile"),
            spot_price=self._get_param("SpotPrice"),
            ebs_optimized=self._get_param("EbsOptimized"),
            associate_public_ip_address=self._get_param("AssociatePublicIpAddress"),
            block_device_mappings=self._get_list_prefix("BlockDeviceMappings.member"),
            instance_id=self._get_param("InstanceId"),
        )
        template = self.response_template(CREATE_LAUNCH_CONFIGURATION_TEMPLATE)
        return template.render()

    def describe_launch_configurations(self):
        names = self._get_multi_param("LaunchConfigurationNames.member")
        all_launch_configurations = self.autoscaling_backend.describe_launch_configurations(
            names
        )
        marker = self._get_param("NextToken")
        all_names = [lc.name for lc in all_launch_configurations]
        if marker:
            start = all_names.index(marker) + 1
        else:
            start = 0
        max_records = self._get_int_param(
            "MaxRecords", 50
        )  # the default is 100, but using 50 to make testing easier
        launch_configurations_resp = all_launch_configurations[
            start : start + max_records
        ]
        next_token = None
        if len(all_launch_configurations) > start + max_records:
            next_token = launch_configurations_resp[-1].name

        template = self.response_template(DESCRIBE_LAUNCH_CONFIGURATIONS_TEMPLATE)
        return template.render(
            launch_configurations=launch_configurations_resp, next_token=next_token
        )

    def delete_launch_configuration(self):
        launch_configurations_name = self.querystring.get("LaunchConfigurationName")[0]
        self.autoscaling_backend.delete_launch_configuration(launch_configurations_name)
        template = self.response_template(DELETE_LAUNCH_CONFIGURATION_TEMPLATE)
        return template.render()

    def create_auto_scaling_group(self):
        self.autoscaling_backend.create_auto_scaling_group(
            name=self._get_param("AutoScalingGroupName"),
            availability_zones=self._get_multi_param("AvailabilityZones.member"),
            desired_capacity=self._get_int_param("DesiredCapacity"),
            max_size=self._get_int_param("MaxSize"),
            min_size=self._get_int_param("MinSize"),
            instance_id=self._get_param("InstanceId"),
            launch_config_name=self._get_param("LaunchConfigurationName"),
            launch_template=self._get_dict_param("LaunchTemplate."),
            vpc_zone_identifier=self._get_param("VPCZoneIdentifier"),
            default_cooldown=self._get_int_param("DefaultCooldown"),
            health_check_period=self._get_int_param("HealthCheckGracePeriod"),
            health_check_type=self._get_param("HealthCheckType"),
            load_balancers=self._get_multi_param("LoadBalancerNames.member"),
            target_group_arns=self._get_multi_param("TargetGroupARNs.member"),
            placement_group=self._get_param("PlacementGroup"),
            termination_policies=self._get_multi_param("TerminationPolicies.member"),
            tags=self._get_list_prefix("Tags.member"),
            new_instances_protected_from_scale_in=self._get_bool_param(
                "NewInstancesProtectedFromScaleIn", False
            ),
        )
        template = self.response_template(CREATE_AUTOSCALING_GROUP_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def attach_instances(self):
        group_name = self._get_param("AutoScalingGroupName")
        instance_ids = self._get_multi_param("InstanceIds.member")
        self.autoscaling_backend.attach_instances(group_name, instance_ids)
        template = self.response_template(ATTACH_INSTANCES_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def set_instance_health(self):
        instance_id = self._get_param("InstanceId")
        health_status = self._get_param("HealthStatus")
        if health_status not in ["Healthy", "Unhealthy"]:
            raise ValueError("Valid instance health states are: [Healthy, Unhealthy]")
        should_respect_grace_period = self._get_param("ShouldRespectGracePeriod")
        self.autoscaling_backend.set_instance_health(
            instance_id, health_status, should_respect_grace_period
        )
        template = self.response_template(SET_INSTANCE_HEALTH_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def detach_instances(self):
        group_name = self._get_param("AutoScalingGroupName")
        instance_ids = self._get_multi_param("InstanceIds.member")
        should_decrement_string = self._get_param("ShouldDecrementDesiredCapacity")
        if should_decrement_string == "true":
            should_decrement = True
        else:
            should_decrement = False
        detached_instances = self.autoscaling_backend.detach_instances(
            group_name, instance_ids, should_decrement
        )
        template = self.response_template(DETACH_INSTANCES_TEMPLATE)
        return template.render(detached_instances=detached_instances)

    @amz_crc32
    @amzn_request_id
    def attach_load_balancer_target_groups(self):
        group_name = self._get_param("AutoScalingGroupName")
        target_group_arns = self._get_multi_param("TargetGroupARNs.member")

        self.autoscaling_backend.attach_load_balancer_target_groups(
            group_name, target_group_arns
        )
        template = self.response_template(ATTACH_LOAD_BALANCER_TARGET_GROUPS_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def describe_load_balancer_target_groups(self):
        group_name = self._get_param("AutoScalingGroupName")
        target_group_arns = self.autoscaling_backend.describe_load_balancer_target_groups(
            group_name
        )
        template = self.response_template(DESCRIBE_LOAD_BALANCER_TARGET_GROUPS)
        return template.render(target_group_arns=target_group_arns)

    @amz_crc32
    @amzn_request_id
    def detach_load_balancer_target_groups(self):
        group_name = self._get_param("AutoScalingGroupName")
        target_group_arns = self._get_multi_param("TargetGroupARNs.member")

        self.autoscaling_backend.detach_load_balancer_target_groups(
            group_name, target_group_arns
        )
        template = self.response_template(DETACH_LOAD_BALANCER_TARGET_GROUPS_TEMPLATE)
        return template.render()

    def describe_auto_scaling_groups(self):
        names = self._get_multi_param("AutoScalingGroupNames.member")
        token = self._get_param("NextToken")
        all_groups = self.autoscaling_backend.describe_auto_scaling_groups(names)
        all_names = [group.name for group in all_groups]
        if token:
            start = all_names.index(token) + 1
        else:
            start = 0
        max_records = self._get_int_param("MaxRecords", 50)
        if max_records > 100:
            raise ValueError
        groups = all_groups[start : start + max_records]
        next_token = None
        if max_records and len(all_groups) > start + max_records:
            next_token = groups[-1].name
        template = self.response_template(DESCRIBE_AUTOSCALING_GROUPS_TEMPLATE)
        return template.render(groups=groups, next_token=next_token)

    def update_auto_scaling_group(self):
        self.autoscaling_backend.update_auto_scaling_group(
            name=self._get_param("AutoScalingGroupName"),
            availability_zones=self._get_multi_param("AvailabilityZones.member"),
            desired_capacity=self._get_int_param("DesiredCapacity"),
            max_size=self._get_int_param("MaxSize"),
            min_size=self._get_int_param("MinSize"),
            launch_config_name=self._get_param("LaunchConfigurationName"),
            launch_template=self._get_dict_param("LaunchTemplate."),
            vpc_zone_identifier=self._get_param("VPCZoneIdentifier"),
            default_cooldown=self._get_int_param("DefaultCooldown"),
            health_check_period=self._get_int_param("HealthCheckGracePeriod"),
            health_check_type=self._get_param("HealthCheckType"),
            placement_group=self._get_param("PlacementGroup"),
            termination_policies=self._get_multi_param("TerminationPolicies.member"),
            new_instances_protected_from_scale_in=self._get_bool_param(
                "NewInstancesProtectedFromScaleIn", None
            ),
        )
        template = self.response_template(UPDATE_AUTOSCALING_GROUP_TEMPLATE)
        return template.render()

    def delete_auto_scaling_group(self):
        group_name = self._get_param("AutoScalingGroupName")
        self.autoscaling_backend.delete_auto_scaling_group(group_name)
        template = self.response_template(DELETE_AUTOSCALING_GROUP_TEMPLATE)
        return template.render()

    def set_desired_capacity(self):
        group_name = self._get_param("AutoScalingGroupName")
        desired_capacity = self._get_int_param("DesiredCapacity")
        self.autoscaling_backend.set_desired_capacity(group_name, desired_capacity)
        template = self.response_template(SET_DESIRED_CAPACITY_TEMPLATE)
        return template.render()

    def create_or_update_tags(self):
        tags = self._get_list_prefix("Tags.member")

        self.autoscaling_backend.create_or_update_tags(tags)
        template = self.response_template(UPDATE_AUTOSCALING_GROUP_TEMPLATE)
        return template.render()

    def describe_auto_scaling_instances(self):
        instance_states = self.autoscaling_backend.describe_auto_scaling_instances(
            instance_ids=self._get_multi_param("InstanceIds.member")
        )
        template = self.response_template(DESCRIBE_AUTOSCALING_INSTANCES_TEMPLATE)
        return template.render(instance_states=instance_states)

    def put_scaling_policy(self):
        policy = self.autoscaling_backend.create_autoscaling_policy(
            name=self._get_param("PolicyName"),
            policy_type=self._get_param("PolicyType"),
            adjustment_type=self._get_param("AdjustmentType"),
            as_name=self._get_param("AutoScalingGroupName"),
            scaling_adjustment=self._get_int_param("ScalingAdjustment"),
            cooldown=self._get_int_param("Cooldown"),
        )
        template = self.response_template(CREATE_SCALING_POLICY_TEMPLATE)
        return template.render(policy=policy)

    def describe_policies(self):
        policies = self.autoscaling_backend.describe_policies(
            autoscaling_group_name=self._get_param("AutoScalingGroupName"),
            policy_names=self._get_multi_param("PolicyNames.member"),
            policy_types=self._get_multi_param("PolicyTypes.member"),
        )
        template = self.response_template(DESCRIBE_SCALING_POLICIES_TEMPLATE)
        return template.render(policies=policies)

    def delete_policy(self):
        group_name = self._get_param("PolicyName")
        self.autoscaling_backend.delete_policy(group_name)
        template = self.response_template(DELETE_POLICY_TEMPLATE)
        return template.render()

    def execute_policy(self):
        group_name = self._get_param("PolicyName")
        self.autoscaling_backend.execute_policy(group_name)
        template = self.response_template(EXECUTE_POLICY_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def attach_load_balancers(self):
        group_name = self._get_param("AutoScalingGroupName")
        load_balancer_names = self._get_multi_param("LoadBalancerNames.member")
        self.autoscaling_backend.attach_load_balancers(group_name, load_balancer_names)
        template = self.response_template(ATTACH_LOAD_BALANCERS_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def describe_load_balancers(self):
        group_name = self._get_param("AutoScalingGroupName")
        load_balancers = self.autoscaling_backend.describe_load_balancers(group_name)
        template = self.response_template(DESCRIBE_LOAD_BALANCERS_TEMPLATE)
        return template.render(load_balancers=load_balancers)

    @amz_crc32
    @amzn_request_id
    def detach_load_balancers(self):
        group_name = self._get_param("AutoScalingGroupName")
        load_balancer_names = self._get_multi_param("LoadBalancerNames.member")
        self.autoscaling_backend.detach_load_balancers(group_name, load_balancer_names)
        template = self.response_template(DETACH_LOAD_BALANCERS_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def enter_standby(self):
        group_name = self._get_param("AutoScalingGroupName")
        instance_ids = self._get_multi_param("InstanceIds.member")
        should_decrement_string = self._get_param("ShouldDecrementDesiredCapacity")
        if should_decrement_string == "true":
            should_decrement = True
        else:
            should_decrement = False
        (
            standby_instances,
            original_size,
            desired_capacity,
        ) = self.autoscaling_backend.enter_standby_instances(
            group_name, instance_ids, should_decrement
        )
        template = self.response_template(ENTER_STANDBY_TEMPLATE)
        return template.render(
            standby_instances=standby_instances,
            should_decrement=should_decrement,
            original_size=original_size,
            desired_capacity=desired_capacity,
            timestamp=iso_8601_datetime_with_milliseconds(datetime.datetime.utcnow()),
        )

    @amz_crc32
    @amzn_request_id
    def exit_standby(self):
        group_name = self._get_param("AutoScalingGroupName")
        instance_ids = self._get_multi_param("InstanceIds.member")
        (
            standby_instances,
            original_size,
            desired_capacity,
        ) = self.autoscaling_backend.exit_standby_instances(group_name, instance_ids)
        template = self.response_template(EXIT_STANDBY_TEMPLATE)
        return template.render(
            standby_instances=standby_instances,
            original_size=original_size,
            desired_capacity=desired_capacity,
            timestamp=iso_8601_datetime_with_milliseconds(datetime.datetime.utcnow()),
        )

    def suspend_processes(self):
        autoscaling_group_name = self._get_param("AutoScalingGroupName")
        scaling_processes = self._get_multi_param("ScalingProcesses.member")
        self.autoscaling_backend.suspend_processes(
            autoscaling_group_name, scaling_processes
        )
        template = self.response_template(SUSPEND_PROCESSES_TEMPLATE)
        return template.render()

    def set_instance_protection(self):
        group_name = self._get_param("AutoScalingGroupName")
        instance_ids = self._get_multi_param("InstanceIds.member")
        protected_from_scale_in = self._get_bool_param("ProtectedFromScaleIn")
        self.autoscaling_backend.set_instance_protection(
            group_name, instance_ids, protected_from_scale_in
        )
        template = self.response_template(SET_INSTANCE_PROTECTION_TEMPLATE)
        return template.render()

    @amz_crc32
    @amzn_request_id
    def terminate_instance_in_auto_scaling_group(self):
        instance_id = self._get_param("InstanceId")
        should_decrement_string = self._get_param("ShouldDecrementDesiredCapacity")
        if should_decrement_string == "true":
            should_decrement = True
        else:
            should_decrement = False
        (
            instance,
            original_size,
            desired_capacity,
        ) = self.autoscaling_backend.terminate_instance(instance_id, should_decrement)
        template = self.response_template(TERMINATE_INSTANCES_TEMPLATE)
        return template.render(
            instance=instance,
            should_decrement=should_decrement,
            original_size=original_size,
            desired_capacity=desired_capacity,
            timestamp=iso_8601_datetime_with_milliseconds(datetime.datetime.utcnow()),
        )


CREATE_LAUNCH_CONFIGURATION_TEMPLATE = """<CreateLaunchConfigurationResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<ResponseMetadata>
   <RequestId>7c6e177f-f082-11e1-ac58-3714bEXAMPLE</RequestId>
</ResponseMetadata>
</CreateLaunchConfigurationResponse>"""

DESCRIBE_LAUNCH_CONFIGURATIONS_TEMPLATE = """<DescribeLaunchConfigurationsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribeLaunchConfigurationsResult>
    <LaunchConfigurations>
      {% for launch_configuration in launch_configurations %}
        <member>
          <AssociatePublicIpAddress>{{ launch_configuration.associate_public_ip_address }}</AssociatePublicIpAddress>
          <SecurityGroups>
            {% for security_group in launch_configuration.security_groups %}
              <member>{{ security_group }}</member>
            {% endfor %}
          </SecurityGroups>
          <CreatedTime>2013-01-21T23:04:42.200Z</CreatedTime>
          <KernelId>{{ launch_configuration.kernel_id }}</KernelId>
          {% if launch_configuration.instance_profile_name %}
            <IamInstanceProfile>{{ launch_configuration.instance_profile_name }}</IamInstanceProfile>
          {% endif %}
          <LaunchConfigurationName>{{ launch_configuration.name }}</LaunchConfigurationName>
          {% if launch_configuration.user_data %}
            <UserData>{{ launch_configuration.user_data }}</UserData>
          {% else %}
            <UserData/>
          {% endif %}
          <InstanceType>{{ launch_configuration.instance_type }}</InstanceType>
          <LaunchConfigurationARN>arn:aws:autoscaling:us-east-1:803981987763:launchConfiguration:9dbbbf87-6141-428a-a409-0752edbe6cad:launchConfigurationName/{{ launch_configuration.name }}</LaunchConfigurationARN>
          {% if launch_configuration.block_device_mappings %}
            <BlockDeviceMappings>
            {% for mount_point, mapping in launch_configuration.block_device_mappings.items() %}
              <member>
                <DeviceName>{{ mount_point }}</DeviceName>
                {% if mapping.ephemeral_name %}
                <VirtualName>{{ mapping.ephemeral_name }}</VirtualName>
                {% else %}
                <Ebs>
                {% if mapping.snapshot_id %}
                  <SnapshotId>{{ mapping.snapshot_id }}</SnapshotId>
                {% endif %}
                {% if mapping.size %}
                  <VolumeSize>{{ mapping.size }}</VolumeSize>
                {% endif %}
                {% if mapping.iops %}
                  <Iops>{{ mapping.iops }}</Iops>
                {% endif %}
                  <DeleteOnTermination>{{ mapping.delete_on_termination }}</DeleteOnTermination>
                  <VolumeType>{{ mapping.volume_type }}</VolumeType>
                </Ebs>
                {% endif %}
              </member>
            {% endfor %}
            </BlockDeviceMappings>
          {% else %}
            <BlockDeviceMappings/>
          {% endif %}
          <ImageId>{{ launch_configuration.image_id }}</ImageId>
          {% if launch_configuration.key_name %}
            <KeyName>{{ launch_configuration.key_name }}</KeyName>
          {% else %}
            <KeyName/>
          {% endif %}
          <RamdiskId>{{ launch_configuration.ramdisk_id }}</RamdiskId>
          <EbsOptimized>{{ launch_configuration.ebs_optimized }}</EbsOptimized>
          <InstanceMonitoring>
            <Enabled>{{ launch_configuration.instance_monitoring_enabled }}</Enabled>
          </InstanceMonitoring>
          {% if launch_configuration.spot_price %}
            <SpotPrice>{{ launch_configuration.spot_price }}</SpotPrice>
          {% endif %}
        </member>
      {% endfor %}
    </LaunchConfigurations>
    {% if next_token %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
  </DescribeLaunchConfigurationsResult>
  <ResponseMetadata>
    <RequestId>d05a22f8-b690-11e2-bf8e-2113fEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeLaunchConfigurationsResponse>"""

DELETE_LAUNCH_CONFIGURATION_TEMPLATE = """<DeleteLaunchConfigurationResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>7347261f-97df-11e2-8756-35eEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteLaunchConfigurationResponse>"""

CREATE_AUTOSCALING_GROUP_TEMPLATE = """<CreateAutoScalingGroupResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<ResponseMetadata>
<RequestId>8d798a29-f083-11e1-bdfb-cb223EXAMPLE</RequestId>
</ResponseMetadata>
</CreateAutoScalingGroupResponse>"""

ATTACH_LOAD_BALANCER_TARGET_GROUPS_TEMPLATE = """<AttachLoadBalancerTargetGroupsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<AttachLoadBalancerTargetGroupsResult>
</AttachLoadBalancerTargetGroupsResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</AttachLoadBalancerTargetGroupsResponse>"""

ATTACH_INSTANCES_TEMPLATE = """<AttachInstancesResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<AttachInstancesResult>
</AttachInstancesResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</AttachInstancesResponse>"""

DESCRIBE_LOAD_BALANCER_TARGET_GROUPS = """<DescribeLoadBalancerTargetGroupsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<DescribeLoadBalancerTargetGroupsResult>
  <LoadBalancerTargetGroups>
  {% for arn in target_group_arns %}
    <member>
      <LoadBalancerTargetGroupARN>{{ arn }}</LoadBalancerTargetGroupARN>
      <State>Added</State>
    </member>
  {% endfor %}
  </LoadBalancerTargetGroups>
</DescribeLoadBalancerTargetGroupsResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</DescribeLoadBalancerTargetGroupsResponse>"""

DETACH_INSTANCES_TEMPLATE = """<DetachInstancesResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<DetachInstancesResult>
  <Activities>
    {% for instance in detached_instances %}
    <member>
      <ActivityId>5091cb52-547a-47ce-a236-c9ccbc2cb2c9EXAMPLE</ActivityId>
      <AutoScalingGroupName>{{ group_name }}</AutoScalingGroupName>
      <Cause>
      At 2017-10-15T15:55:21Z instance {{ instance.instance.id }} was detached in response to a user request.
      </Cause>
      <Description>Detaching EC2 instance: {{ instance.instance.id }}</Description>
      <StartTime>2017-10-15T15:55:21Z</StartTime>
      <EndTime>2017-10-15T15:55:21Z</EndTime>
      <StatusCode>InProgress</StatusCode>
      <StatusMessage>InProgress</StatusMessage>
      <Progress>50</Progress>
      <Details>details</Details>
    </member>
    {% endfor %}
  </Activities>
</DetachInstancesResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</DetachInstancesResponse>"""

DETACH_LOAD_BALANCER_TARGET_GROUPS_TEMPLATE = """<DetachLoadBalancerTargetGroupsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<DetachLoadBalancerTargetGroupsResult>
</DetachLoadBalancerTargetGroupsResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</DetachLoadBalancerTargetGroupsResponse>"""

DESCRIBE_AUTOSCALING_GROUPS_TEMPLATE = """<DescribeAutoScalingGroupsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<DescribeAutoScalingGroupsResult>
    <AutoScalingGroups>
      {% for group in groups %}
      <member>
        <Tags>
          {% for tag in group.tags %}
          <member>
            <ResourceType>{{ tag.resource_type or tag.ResourceType }}</ResourceType>
            <ResourceId>{{ tag.resource_id or tag.ResourceId }}</ResourceId>
            <PropagateAtLaunch>{{ tag.propagate_at_launch or tag.PropagateAtLaunch }}</PropagateAtLaunch>
            <Key>{{ tag.key or tag.Key }}</Key>
            <Value>{{ tag.value or tag.Value }}</Value>
          </member>
          {% endfor %}
        </Tags>
        <SuspendedProcesses>
          {% for suspended_process in group.suspended_processes %}
          <member>
            <ProcessName>{{suspended_process}}</ProcessName>
            <SuspensionReason></SuspensionReason>
          </member>
          {% endfor %}
        </SuspendedProcesses>
        <AutoScalingGroupName>{{ group.name }}</AutoScalingGroupName>
        <HealthCheckType>{{ group.health_check_type }}</HealthCheckType>
        <CreatedTime>2013-05-06T17:47:15.107Z</CreatedTime>
        <EnabledMetrics/>
        {% if group.launch_config_name %}
        <LaunchConfigurationName>{{ group.launch_config_name }}</LaunchConfigurationName>
        {% elif group.launch_template %}
        <LaunchTemplate>
          <LaunchTemplateId>{{ group.launch_template.id }}</LaunchTemplateId>
          <Version>{{ group.launch_template_version }}</Version>
          <LaunchTemplateName>{{ group.launch_template.name }}</LaunchTemplateName>
        </LaunchTemplate>
        {% endif %}
        <Instances>
          {% for instance_state in group.instance_states %}
          <member>
            <HealthStatus>{{ instance_state.health_status }}</HealthStatus>
            <AvailabilityZone>{{ instance_state.instance.placement }}</AvailabilityZone>
            <InstanceId>{{ instance_state.instance.id }}</InstanceId>
            <InstanceType>{{ instance_state.instance.instance_type }}</InstanceType>
            {% if group.launch_config_name %}
            <LaunchConfigurationName>{{ group.launch_config_name }}</LaunchConfigurationName>
            {% elif group.launch_template %}
            <LaunchTemplate>
              <LaunchTemplateId>{{ group.launch_template.id }}</LaunchTemplateId>
              <Version>{{ group.launch_template_version }}</Version>
              <LaunchTemplateName>{{ group.launch_template.name }}</LaunchTemplateName>
            </LaunchTemplate>
            {% endif %}
            <LifecycleState>{{ instance_state.lifecycle_state }}</LifecycleState>
            <ProtectedFromScaleIn>{{ instance_state.protected_from_scale_in|string|lower }}</ProtectedFromScaleIn>
          </member>
          {% endfor %}
        </Instances>
        <DesiredCapacity>{{ group.desired_capacity }}</DesiredCapacity>
        <AvailabilityZones>
          {% for availability_zone in group.availability_zones %}
          <member>{{ availability_zone }}</member>
          {% endfor %}
        </AvailabilityZones>
        {% if group.load_balancers %}
          <LoadBalancerNames>
          {% for load_balancer in group.load_balancers %}
            <member>{{ load_balancer }}</member>
          {% endfor %}
          </LoadBalancerNames>
        {% else %}
          <LoadBalancerNames/>
        {% endif %}
        {% if group.target_group_arns %}
          <TargetGroupARNs>
          {% for target_group_arn in group.target_group_arns %}
            <member>{{ target_group_arn }}</member>
          {% endfor %}
          </TargetGroupARNs>
        {% else %}
          <TargetGroupARNs/>
        {% endif %}
        <MinSize>{{ group.min_size }}</MinSize>
        {% if group.vpc_zone_identifier %}
          <VPCZoneIdentifier>{{ group.vpc_zone_identifier }}</VPCZoneIdentifier>
        {% else %}
          <VPCZoneIdentifier/>
        {% endif %}
        <HealthCheckGracePeriod>{{ group.health_check_period }}</HealthCheckGracePeriod>
        <DefaultCooldown>{{ group.default_cooldown }}</DefaultCooldown>
        <AutoScalingGroupARN>arn:aws:autoscaling:us-east-1:803981987763:autoScalingGroup:ca861182-c8f9-4ca7-b1eb-cd35505f5ebb:autoScalingGroupName/{{ group.name }}</AutoScalingGroupARN>
        {% if group.termination_policies %}
        <TerminationPolicies>
          {% for policy in group.termination_policies %}
          <member>{{ policy }}</member>
          {% endfor %}
        </TerminationPolicies>
        {% else %}
        <TerminationPolicies/>
        {% endif %}
        <MaxSize>{{ group.max_size }}</MaxSize>
        {% if group.placement_group %}
        <PlacementGroup>{{ group.placement_group }}</PlacementGroup>
        {% endif %}
        <NewInstancesProtectedFromScaleIn>{{ group.new_instances_protected_from_scale_in|string|lower }}</NewInstancesProtectedFromScaleIn>
      </member>
      {% endfor %}
    </AutoScalingGroups>
    {% if next_token %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
  </DescribeAutoScalingGroupsResult>
  <ResponseMetadata>
    <RequestId>0f02a07d-b677-11e2-9eb0-dd50EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeAutoScalingGroupsResponse>"""

UPDATE_AUTOSCALING_GROUP_TEMPLATE = """<UpdateAutoScalingGroupResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>adafead0-ab8a-11e2-ba13-ab0ccEXAMPLE</RequestId>
  </ResponseMetadata>
</UpdateAutoScalingGroupResponse>"""

DELETE_AUTOSCALING_GROUP_TEMPLATE = """<DeleteAutoScalingGroupResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>70a76d42-9665-11e2-9fdf-211deEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteAutoScalingGroupResponse>"""

DESCRIBE_AUTOSCALING_INSTANCES_TEMPLATE = """<DescribeAutoScalingInstancesResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribeAutoScalingInstancesResult>
    <AutoScalingInstances>
      {% for instance_state in instance_states %}
      <member>
        <HealthStatus>{{ instance_state.health_status }}</HealthStatus>
        <AutoScalingGroupName>{{ instance_state.instance.autoscaling_group.name }}</AutoScalingGroupName>
        <AvailabilityZone>{{ instance_state.instance.placement }}</AvailabilityZone>
        <InstanceId>{{ instance_state.instance.id }}</InstanceId>
        <InstanceType>{{ instance_state.instance.instance_type }}</InstanceType>
        {% if instance_state.instance.autoscaling_group.launch_config_name %}
        <LaunchConfigurationName>{{ instance_state.instance.autoscaling_group.launch_config_name }}</LaunchConfigurationName>
        {% elif instance_state.instance.autoscaling_group.launch_template %}
        <LaunchTemplate>
          <LaunchTemplateId>{{ instance_state.instance.autoscaling_group.launch_template.id }}</LaunchTemplateId>
          <Version>{{ instance_state.instance.autoscaling_group.launch_template_version }}</Version>
          <LaunchTemplateName>{{ instance_state.instance.autoscaling_group.launch_template.name }}</LaunchTemplateName>
        </LaunchTemplate>
        {% endif %}
        <LifecycleState>{{ instance_state.lifecycle_state }}</LifecycleState>
        <ProtectedFromScaleIn>{{ instance_state.protected_from_scale_in|string|lower }}</ProtectedFromScaleIn>
      </member>
      {% endfor %}
    </AutoScalingInstances>
  </DescribeAutoScalingInstancesResult>
  <ResponseMetadata>
    <RequestId>df992dc3-b72f-11e2-81e1-750aa6EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeAutoScalingInstancesResponse>"""

CREATE_SCALING_POLICY_TEMPLATE = """<PutScalingPolicyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <PutScalingPolicyResult>
    <PolicyARN>arn:aws:autoscaling:us-east-1:803981987763:scalingPolicy:b0dcf5e8
-02e6-4e31-9719-0675d0dc31ae:autoScalingGroupName/my-test-asg:policyName/my-scal
eout-policy</PolicyARN>
  </PutScalingPolicyResult>
  <ResponseMetadata>
    <RequestId>3cfc6fef-c08b-11e2-a697-2922EXAMPLE</RequestId>
  </ResponseMetadata>
</PutScalingPolicyResponse>"""

DESCRIBE_SCALING_POLICIES_TEMPLATE = """<DescribePoliciesResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribePoliciesResult>
    <ScalingPolicies>
      {% for policy in policies %}
      <member>
        <PolicyARN>arn:aws:autoscaling:us-east-1:803981987763:scalingPolicy:c322
761b-3172-4d56-9a21-0ed9d6161d67:autoScalingGroupName/my-test-asg:policyName/MyScaleDownPolicy</PolicyARN>
        <AdjustmentType>{{ policy.adjustment_type }}</AdjustmentType>
        <ScalingAdjustment>{{ policy.scaling_adjustment }}</ScalingAdjustment>
        <PolicyName>{{ policy.name }}</PolicyName>
        <PolicyType>{{ policy.policy_type }}</PolicyType>
        <AutoScalingGroupName>{{ policy.as_name }}</AutoScalingGroupName>
        <Cooldown>{{ policy.cooldown }}</Cooldown>
        <Alarms/>
      </member>
      {% endfor %}
    </ScalingPolicies>
  </DescribePoliciesResult>
  <ResponseMetadata>
    <RequestId>ec3bffad-b739-11e2-b38d-15fbEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribePoliciesResponse>"""

SET_DESIRED_CAPACITY_TEMPLATE = """<SetDesiredCapacityResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>9fb7e2db-6998-11e2-a985-57c82EXAMPLE</RequestId>
  </ResponseMetadata>
</SetDesiredCapacityResponse>"""

EXECUTE_POLICY_TEMPLATE = """<ExecuteScalingPolicyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>70a76d42-9665-11e2-9fdf-211deEXAMPLE</RequestId>
  </ResponseMetadata>
</ExecuteScalingPolicyResponse>"""

DELETE_POLICY_TEMPLATE = """<DeleteScalingPolicyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ResponseMetadata>
    <RequestId>70a76d42-9665-11e2-9fdf-211deEXAMPLE</RequestId>
  </ResponseMetadata>
</DeleteScalingPolicyResponse>"""

ATTACH_LOAD_BALANCERS_TEMPLATE = """<AttachLoadBalancersResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<AttachLoadBalancersResult></AttachLoadBalancersResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</AttachLoadBalancersResponse>"""

DESCRIBE_LOAD_BALANCERS_TEMPLATE = """<DescribeLoadBalancersResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<DescribeLoadBalancersResult>
  <LoadBalancers>
    {% for load_balancer in load_balancers %}
      <member>
        <LoadBalancerName>{{ load_balancer }}</LoadBalancerName>
        <State>Added</State>
      </member>
    {% endfor %}
  </LoadBalancers>
</DescribeLoadBalancersResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</DescribeLoadBalancersResponse>"""

DETACH_LOAD_BALANCERS_TEMPLATE = """<DetachLoadBalancersResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<DetachLoadBalancersResult></DetachLoadBalancersResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</DetachLoadBalancersResponse>"""

SUSPEND_PROCESSES_TEMPLATE = """<SuspendProcessesResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<ResponseMetadata>
   <RequestId>7c6e177f-f082-11e1-ac58-3714bEXAMPLE</RequestId>
</ResponseMetadata>
</SuspendProcessesResponse>"""

SET_INSTANCE_HEALTH_TEMPLATE = """<SetInstanceHealthResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<SetInstanceHealthResponse></SetInstanceHealthResponse>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</SetInstanceHealthResponse>"""

SET_INSTANCE_PROTECTION_TEMPLATE = """<SetInstanceProtectionResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
<SetInstanceProtectionResult></SetInstanceProtectionResult>
<ResponseMetadata>
<RequestId></RequestId>
</ResponseMetadata>
</SetInstanceProtectionResponse>"""

ENTER_STANDBY_TEMPLATE = """<EnterStandbyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <EnterStandbyResult>
    <Activities>
      {% for instance in standby_instances %}
      <member>
        <ActivityId>12345678-1234-1234-1234-123456789012</ActivityId>
        <AutoScalingGroupName>{{ group_name }}</AutoScalingGroupName>
        {% if should_decrement %}
        <Cause>At {{ timestamp }} instance {{ instance.instance.id }} was moved to standby in response to a user request, shrinking the capacity from {{ original_size }} to {{ desired_capacity }}.</Cause>
        {% else %}
        <Cause>At {{ timestamp }} instance {{ instance.instance.id }} was moved to standby in response to a user request.</Cause>
        {% endif %}
        <Description>Moving EC2 instance to Standby: {{ instance.instance.id }}</Description>
        <Progress>50</Progress>
        <StartTime>{{ timestamp }}</StartTime>
        <Details>{&quot;Subnet ID&quot;:&quot;??&quot;,&quot;Availability Zone&quot;:&quot;{{ instance.instance.placement }}&quot;}</Details>
        <StatusCode>InProgress</StatusCode>
      </member>
      {% endfor %}
    </Activities>
  </EnterStandbyResult>
  <ResponseMetadata>
    <RequestId>7c6e177f-f082-11e1-ac58-3714bEXAMPLE</RequestId>
  </ResponseMetadata>
</EnterStandbyResponse>"""

EXIT_STANDBY_TEMPLATE = """<ExitStandbyResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <ExitStandbyResult>
    <Activities>
      {% for instance in standby_instances %}
      <member>
        <ActivityId>12345678-1234-1234-1234-123456789012</ActivityId>
        <AutoScalingGroupName>{{ group_name }}</AutoScalingGroupName>
        <Description>Moving EC2 instance out of Standby: {{ instance.instance.id }}</Description>
        <Progress>30</Progress>
        <Cause>At {{ timestamp }} instance {{ instance.instance.id }} was moved out of standby in response to a user request, increasing the capacity from {{ original_size }} to {{ desired_capacity }}.</Cause>
        <StartTime>{{ timestamp }}</StartTime>
        <Details>{&quot;Subnet ID&quot;:&quot;??&quot;,&quot;Availability Zone&quot;:&quot;{{ instance.instance.placement }}&quot;}</Details>
        <StatusCode>PreInService</StatusCode>
      </member>
      {% endfor %}
    </Activities>
  </ExitStandbyResult>
  <ResponseMetadata>
    <RequestId>7c6e177f-f082-11e1-ac58-3714bEXAMPLE</RequestId>
  </ResponseMetadata>
</ExitStandbyResponse>"""

TERMINATE_INSTANCES_TEMPLATE = """<TerminateInstanceInAutoScalingGroupResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <TerminateInstanceInAutoScalingGroupResult>
    <Activity>
      <ActivityId>35b5c464-0b63-2fc7-1611-467d4a7f2497EXAMPLE</ActivityId>
      <AutoScalingGroupName>{{ group_name }}</AutoScalingGroupName>
      {% if should_decrement %}
      <Cause>At {{ timestamp }} instance {{ instance.instance.id }} was taken out of service in response to a user request, shrinking the capacity from {{ original_size }} to {{ desired_capacity }}.</Cause>
      {% else %}
      <Cause>At {{ timestamp }} instance {{ instance.instance.id }} was taken out of service in response to a user request.</Cause>
      {% endif %}
      <Description>Terminating EC2 instance: {{ instance.instance.id }}</Description>
      <Progress>0</Progress>
      <StartTime>{{ timestamp }}</StartTime>
      <Details>{&quot;Subnet ID&quot;:&quot;??&quot;,&quot;Availability Zone&quot;:&quot;{{ instance.instance.placement }}&quot;}</Details>
      <StatusCode>InProgress</StatusCode>
    </Activity>
  </TerminateInstanceInAutoScalingGroupResult>
  <ResponseMetadata>
    <RequestId>a1ba8fb9-31d6-4d9a-ace1-a7f76749df11EXAMPLE</RequestId>
  </ResponseMetadata>
</TerminateInstanceInAutoScalingGroupResponse>"""
