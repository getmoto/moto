from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import ActionResult, BaseResponse, EmptyResult
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.utilities.aws_headers import amz_crc32

from .models import AutoScalingBackend, autoscaling_backends


class AutoScalingResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="autoscaling")
        # self.automated_parameter_parsing = True

    @property
    def autoscaling_backend(self) -> AutoScalingBackend:
        return autoscaling_backends[self.current_account][self.region]

    @amz_crc32
    def call_action(self) -> TYPE_RESPONSE:
        return super().call_action()

    def create_launch_configuration(self) -> str:
        instance_monitoring_string = self._get_param("InstanceMonitoring.Enabled")
        if instance_monitoring_string == "true":
            instance_monitoring = True
        else:
            instance_monitoring = False
        params = self._get_params()
        self.autoscaling_backend.create_launch_configuration(
            name=params.get("LaunchConfigurationName"),  # type: ignore[arg-type]
            image_id=params.get("ImageId"),  # type: ignore[arg-type]
            key_name=params.get("KeyName"),
            ramdisk_id=params.get("RamdiskId"),  # type: ignore[arg-type]
            kernel_id=params.get("KernelId"),  # type: ignore[arg-type]
            security_groups=self._get_multi_param("SecurityGroups.member"),
            user_data=params.get("UserData"),  # type: ignore[arg-type]
            instance_type=params.get("InstanceType"),  # type: ignore[arg-type]
            instance_monitoring=instance_monitoring,
            instance_profile_name=params.get("IamInstanceProfile"),
            spot_price=params.get("SpotPrice"),
            ebs_optimized=params.get("EbsOptimized"),  # type: ignore[arg-type]
            associate_public_ip_address=params.get("AssociatePublicIpAddress"),  # type: ignore[arg-type]
            block_device_mappings=params.get("BlockDeviceMappings"),  # type: ignore[arg-type]
            instance_id=params.get("InstanceId"),
            metadata_options=params.get("MetadataOptions"),
            classic_link_vpc_id=params.get("ClassicLinkVPCId"),
            classic_link_vpc_security_groups=params.get("ClassicLinkVPCSecurityGroups"),
        )
        return EmptyResult()

    def describe_launch_configurations(self) -> str:
        names = self._get_multi_param("LaunchConfigurationNames.member")
        all_launch_configurations = (
            self.autoscaling_backend.describe_launch_configurations(names)
        )
        marker = self._get_param("NextToken")
        all_names = [lc.name for lc in all_launch_configurations]
        if marker:
            start = all_names.index(marker) + 1
        else:
            start = 0
        # the default is 100, but using 50 to make testing easier
        max_records = self._get_int_param("MaxRecords") or 50
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

    def delete_launch_configuration(self) -> str:
        launch_configurations_name = self.querystring.get("LaunchConfigurationName")[0]  # type: ignore[index]
        self.autoscaling_backend.delete_launch_configuration(launch_configurations_name)
        return EmptyResult()

    def create_auto_scaling_group(self) -> str:
        params = self._get_params()
        self.autoscaling_backend.create_auto_scaling_group(
            name=self._get_param("AutoScalingGroupName"),
            availability_zones=self._get_multi_param("AvailabilityZones.member"),
            desired_capacity=self._get_int_param("DesiredCapacity"),
            max_size=self._get_int_param("MaxSize"),
            min_size=self._get_int_param("MinSize"),
            instance_id=self._get_param("InstanceId"),
            launch_config_name=self._get_param("LaunchConfigurationName"),
            launch_template=self._get_dict_param("LaunchTemplate."),
            mixed_instances_policy=params.get("MixedInstancesPolicy"),
            vpc_zone_identifier=self._get_param("VPCZoneIdentifier"),
            default_cooldown=self._get_int_param("DefaultCooldown"),
            health_check_period=self._get_int_param("HealthCheckGracePeriod"),
            health_check_type=self._get_param("HealthCheckType"),
            load_balancers=self._get_multi_param("LoadBalancerNames.member"),
            target_group_arns=self._get_multi_param("TargetGroupARNs.member"),
            placement_group=self._get_param("PlacementGroup"),
            termination_policies=self._get_multi_param("TerminationPolicies.member"),
            tags=params.get("Tags", []),
            capacity_rebalance=self._get_bool_param("CapacityRebalance", False),
            new_instances_protected_from_scale_in=self._get_bool_param(
                "NewInstancesProtectedFromScaleIn", False
            ),
        )
        return EmptyResult()

    def put_scheduled_update_group_action(self) -> str:
        self.autoscaling_backend.put_scheduled_update_group_action(
            name=self._get_param("AutoScalingGroupName"),
            desired_capacity=self._get_int_param("DesiredCapacity"),
            max_size=self._get_int_param("MaxSize"),
            min_size=self._get_int_param("MinSize"),
            scheduled_action_name=self._get_param("ScheduledActionName"),
            start_time=self._get_param("StartTime"),
            end_time=self._get_param("EndTime"),
            recurrence=self._get_param("Recurrence"),
            timezone=self._get_param("TimeZone"),
        )
        return EmptyResult()

    def batch_put_scheduled_update_group_action(self) -> str:
        failed_actions = (
            self.autoscaling_backend.batch_put_scheduled_update_group_action(
                name=self._get_param("AutoScalingGroupName"),
                actions=self._get_multi_param("ScheduledUpdateGroupActions.member"),
            )
        )
        result = {"FailedScheduledUpdateGroupActions": failed_actions}
        return ActionResult(result)

    def describe_scheduled_actions(self) -> str:
        scheduled_actions = self.autoscaling_backend.describe_scheduled_actions(
            autoscaling_group_name=self._get_param("AutoScalingGroupName"),
            scheduled_action_names=self._get_multi_param("ScheduledActionNames.member"),
        )
        result = {"ScheduledUpdateGroupActions": scheduled_actions}
        return ActionResult(result)

    def delete_scheduled_action(self) -> str:
        auto_scaling_group_name = self._get_param("AutoScalingGroupName")
        scheduled_action_name = self._get_param("ScheduledActionName")
        self.autoscaling_backend.delete_scheduled_action(
            auto_scaling_group_name=auto_scaling_group_name,
            scheduled_action_name=scheduled_action_name,
        )
        return EmptyResult()

    def batch_delete_scheduled_action(self) -> str:
        auto_scaling_group_name = self._get_param("AutoScalingGroupName")
        scheduled_action_names = self._get_multi_param("ScheduledActionNames.member")
        failed_actions = self.autoscaling_backend.batch_delete_scheduled_action(
            auto_scaling_group_name=auto_scaling_group_name,
            scheduled_action_names=scheduled_action_names,
        )
        result = {"FailedScheduledActions": failed_actions}
        return ActionResult(result)

    def describe_scaling_activities(self) -> str:
        return EmptyResult()

    def attach_instances(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        instance_ids = self._get_multi_param("InstanceIds.member")
        self.autoscaling_backend.attach_instances(group_name, instance_ids)
        return EmptyResult()

    def set_instance_health(self) -> str:
        instance_id = self._get_param("InstanceId")
        health_status = self._get_param("HealthStatus")
        if health_status not in ["Healthy", "Unhealthy"]:
            raise ValueError("Valid instance health states are: [Healthy, Unhealthy]")
        self.autoscaling_backend.set_instance_health(instance_id, health_status)
        return EmptyResult()

    def detach_instances(self) -> str:
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

    def attach_load_balancer_target_groups(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        target_group_arns = self._get_multi_param("TargetGroupARNs.member")

        self.autoscaling_backend.attach_load_balancer_target_groups(
            group_name, target_group_arns
        )
        return EmptyResult()

    def describe_load_balancer_target_groups(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        target_group_arns = (
            self.autoscaling_backend.describe_load_balancer_target_groups(group_name)
        )
        result = {
            "LoadBalancerTargetGroups": [
                {"LoadBalancerTargetGroupARN": arn, "State": "Added"}
                for arn in target_group_arns
            ]
        }
        return ActionResult(result)

    def detach_load_balancer_target_groups(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        target_group_arns = self._get_multi_param("TargetGroupARNs.member")

        self.autoscaling_backend.detach_load_balancer_target_groups(
            group_name, target_group_arns
        )
        return EmptyResult()

    def describe_auto_scaling_groups(self) -> str:
        names = self._get_multi_param("AutoScalingGroupNames.member")
        token = self._get_param("NextToken")
        filters = self._get_params().get("Filters", [])
        all_groups = self.autoscaling_backend.describe_auto_scaling_groups(
            names, filters=filters
        )
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

    def update_auto_scaling_group(self) -> str:
        self.autoscaling_backend.update_auto_scaling_group(
            name=self._get_param("AutoScalingGroupName"),
            availability_zones=self._get_multi_param("AvailabilityZones.member"),
            desired_capacity=self._get_int_param("DesiredCapacity"),
            max_size=self._get_int_param("MaxSize"),
            min_size=self._get_int_param("MinSize"),
            launch_config_name=self._get_param("LaunchConfigurationName"),
            launch_template=self._get_dict_param("LaunchTemplate."),
            vpc_zone_identifier=self._get_param("VPCZoneIdentifier"),
            health_check_period=self._get_int_param("HealthCheckGracePeriod"),
            health_check_type=self._get_param("HealthCheckType"),
            new_instances_protected_from_scale_in=self._get_bool_param(
                "NewInstancesProtectedFromScaleIn", None
            ),
        )
        return EmptyResult()

    def delete_auto_scaling_group(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        self.autoscaling_backend.delete_auto_scaling_group(group_name)
        return EmptyResult()

    def set_desired_capacity(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        desired_capacity = self._get_int_param("DesiredCapacity")
        self.autoscaling_backend.set_desired_capacity(group_name, desired_capacity)
        return EmptyResult()

    def create_or_update_tags(self) -> str:
        self.autoscaling_backend.create_or_update_tags(
            self._get_params().get("Tags", [])
        )
        return EmptyResult()

    def delete_tags(self) -> str:
        self.autoscaling_backend.delete_tags(self._get_params().get("Tags", []))
        return EmptyResult()

    def describe_auto_scaling_instances(self) -> str:
        instance_states = self.autoscaling_backend.describe_auto_scaling_instances(
            instance_ids=self._get_multi_param("InstanceIds.member")
        )
        template = self.response_template(DESCRIBE_AUTOSCALING_INSTANCES_TEMPLATE)
        return template.render(instance_states=instance_states)

    def put_lifecycle_hook(self) -> str:
        self.autoscaling_backend.create_lifecycle_hook(
            name=self._get_param("LifecycleHookName"),
            as_name=self._get_param("AutoScalingGroupName"),
            transition=self._get_param("LifecycleTransition"),
            timeout=self._get_int_param("HeartbeatTimeout"),
            result=self._get_param("DefaultResult"),
        )
        return EmptyResult()

    def describe_lifecycle_hooks(self) -> str:
        lifecycle_hooks = self.autoscaling_backend.describe_lifecycle_hooks(
            as_name=self._get_param("AutoScalingGroupName"),
            lifecycle_hook_names=self._get_multi_param("LifecycleHookNames.member"),
        )
        template = self.response_template(DESCRIBE_LIFECYCLE_HOOKS_TEMPLATE)
        return template.render(lifecycle_hooks=lifecycle_hooks)

    def delete_lifecycle_hook(self) -> str:
        as_name = self._get_param("AutoScalingGroupName")
        name = self._get_param("LifecycleHookName")
        self.autoscaling_backend.delete_lifecycle_hook(as_name, name)
        return EmptyResult()

    def put_scaling_policy(self) -> str:
        params = self._get_params()
        policy = self.autoscaling_backend.put_scaling_policy(
            name=params.get("PolicyName"),  # type: ignore[arg-type]
            policy_type=params.get("PolicyType", "SimpleScaling"),
            metric_aggregation_type=params.get("MetricAggregationType"),  # type: ignore[arg-type]
            adjustment_type=params.get("AdjustmentType"),  # type: ignore[arg-type]
            as_name=params.get("AutoScalingGroupName"),  # type: ignore[arg-type]
            min_adjustment_magnitude=params.get("MinAdjustmentMagnitude"),  # type: ignore[arg-type]
            scaling_adjustment=self._get_int_param("ScalingAdjustment"),
            cooldown=self._get_int_param("Cooldown"),
            target_tracking_config=params.get("TargetTrackingConfiguration", {}),
            step_adjustments=params.get("StepAdjustments", []),
            estimated_instance_warmup=params.get("EstimatedInstanceWarmup"),  # type: ignore[arg-type]
            predictive_scaling_configuration=params.get(
                "PredictiveScalingConfiguration", {}
            ),
        )
        return ActionResult({"PolicyArn": policy.arn})

    def describe_policies(self) -> str:
        policies = self.autoscaling_backend.describe_policies(
            autoscaling_group_name=self._get_param("AutoScalingGroupName"),
            policy_names=self._get_multi_param("PolicyNames.member"),
            policy_types=self._get_multi_param("PolicyTypes.member"),
        )
        result = {"ScalingPolicies": policies}
        return ActionResult(result)

    def delete_policy(self) -> str:
        group_name = self._get_param("PolicyName")
        self.autoscaling_backend.delete_policy(group_name)
        return EmptyResult()

    def execute_policy(self) -> str:
        group_name = self._get_param("PolicyName")
        self.autoscaling_backend.execute_policy(group_name)
        return EmptyResult()

    def attach_load_balancers(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        load_balancer_names = self._get_multi_param("LoadBalancerNames.member")
        self.autoscaling_backend.attach_load_balancers(group_name, load_balancer_names)
        return EmptyResult()

    def describe_load_balancers(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        load_balancers = self.autoscaling_backend.describe_load_balancers(group_name)
        result = {
            "LoadBalancers": [
                {"LoadBalancerName": name, "State": "Added"} for name in load_balancers
            ]
        }
        return ActionResult(result)

    def detach_load_balancers(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        load_balancer_names = self._get_multi_param("LoadBalancerNames.member")
        self.autoscaling_backend.detach_load_balancers(group_name, load_balancer_names)
        return EmptyResult()

    def enter_standby(self) -> str:
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
            timestamp=iso_8601_datetime_with_milliseconds(),
        )

    def exit_standby(self) -> str:
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
            timestamp=iso_8601_datetime_with_milliseconds(),
        )

    def suspend_processes(self) -> str:
        autoscaling_group_name = self._get_param("AutoScalingGroupName")
        scaling_processes = self._get_multi_param("ScalingProcesses.member")
        self.autoscaling_backend.suspend_processes(
            autoscaling_group_name, scaling_processes
        )
        return EmptyResult()

    def resume_processes(self) -> str:
        autoscaling_group_name = self._get_param("AutoScalingGroupName")
        scaling_processes = self._get_multi_param("ScalingProcesses.member")
        self.autoscaling_backend.resume_processes(
            autoscaling_group_name, scaling_processes
        )
        return EmptyResult()

    def set_instance_protection(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        instance_ids = self._get_multi_param("InstanceIds.member")
        protected_from_scale_in = self._get_bool_param("ProtectedFromScaleIn")
        self.autoscaling_backend.set_instance_protection(
            group_name, instance_ids, protected_from_scale_in
        )
        return EmptyResult()

    def terminate_instance_in_auto_scaling_group(self) -> str:
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
            timestamp=iso_8601_datetime_with_milliseconds(),
        )

    def describe_tags(self) -> str:
        filters = self._get_params().get("Filters", [])
        tags = self.autoscaling_backend.describe_tags(filters=filters)
        result = {"Tags": tags, "NextToken": None}
        return ActionResult(result)

    def enable_metrics_collection(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        metrics = self._get_params().get("Metrics")
        self.autoscaling_backend.enable_metrics_collection(group_name, metrics)  # type: ignore[arg-type]
        return EmptyResult()

    def put_warm_pool(self) -> str:
        params = self._get_params()
        group_name = params.get("AutoScalingGroupName")
        max_group_prepared_capacity = params.get("MaxGroupPreparedCapacity")
        min_size = params.get("MinSize")
        pool_state = params.get("PoolState")
        instance_reuse_policy = params.get("InstanceReusePolicy")
        self.autoscaling_backend.put_warm_pool(
            group_name=group_name,  # type: ignore[arg-type]
            max_group_prepared_capacity=max_group_prepared_capacity,
            min_size=min_size,
            pool_state=pool_state,
            instance_reuse_policy=instance_reuse_policy,
        )
        return EmptyResult()

    def describe_warm_pool(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        warm_pool = self.autoscaling_backend.describe_warm_pool(group_name=group_name)
        result = {"WarmPoolConfiguration": warm_pool, "Instances": []}
        return ActionResult(result)

    def delete_warm_pool(self) -> str:
        group_name = self._get_param("AutoScalingGroupName")
        self.autoscaling_backend.delete_warm_pool(group_name=group_name)
        return EmptyResult()


DESCRIBE_LAUNCH_CONFIGURATIONS_TEMPLATE = """<DescribeLaunchConfigurationsResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribeLaunchConfigurationsResult>
    <LaunchConfigurations>
      {% for launch_configuration in launch_configurations %}
        <member>
          <AssociatePublicIpAddress>{{ 'true' if launch_configuration.associate_public_ip_address else 'false' }}</AssociatePublicIpAddress>
          {% if launch_configuration.classic_link_vpc_id %}
          <ClassicLinkVPCId>{{ launch_configuration.classic_link_vpc_id }}</ClassicLinkVPCId>
          {% endif %}
          {% if launch_configuration.classic_link_vpc_security_groups %}
          <ClassicLinkVPCSecurityGroups>
            {% for sg in launch_configuration.classic_link_vpc_security_groups %}
            <member>{{ sg }}</member>
            {% endfor %}
          </ClassicLinkVPCSecurityGroups>
          {% endif %}
          <SecurityGroups>
            {% for security_group in launch_configuration.security_groups %}
              <member>{{ security_group }}</member>
            {% endfor %}
          </SecurityGroups>
          <CreatedTime>2013-01-21T23:04:42.200Z</CreatedTime>
          {% if launch_configuration.kernel_id %}
          <KernelId>{{ launch_configuration.kernel_id }}</KernelId>
          {% else %}
          <KernelId/>
          {% endif %}
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
          <LaunchConfigurationARN>{{ launch_configuration.arn }}</LaunchConfigurationARN>
          {% if launch_configuration.block_device_mappings %}
            <BlockDeviceMappings>
            {% for mount_point, mapping in launch_configuration.block_device_mappings.items() %}
              <member>
                <DeviceName>{{ mount_point }}</DeviceName>
                {% if mapping.ephemeral_name %}
                <VirtualName>{{ mapping.ephemeral_name }}</VirtualName>
                {% elif mapping.no_device %}
                <NoDevice>true</NoDevice>
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
                {% if mapping.throughput %}
                  <Throughput>{{ mapping.throughput }}</Throughput>
                {% endif %}
                {% if mapping.delete_on_termination is not none %}
                  <DeleteOnTermination>{{ mapping.delete_on_termination }}</DeleteOnTermination>
                {% endif %}
                {% if mapping.volume_type %}
                  <VolumeType>{{ mapping.volume_type }}</VolumeType>
                {% endif %}
                  {% if mapping.encrypted %}
                  <Encrypted>{{ mapping.encrypted }}</Encrypted>
                  {% endif %}
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
          {% if launch_configuration.ramdisk_id %}
          <RamdiskId>{{ launch_configuration.ramdisk_id }}</RamdiskId>
          {% else %}
          <RamdiskId/>
          {% endif %}
          <EbsOptimized>{{ launch_configuration.ebs_optimized }}</EbsOptimized>
          <InstanceMonitoring>
            <Enabled>{{ launch_configuration.instance_monitoring_enabled }}</Enabled>
          </InstanceMonitoring>
          {% if launch_configuration.spot_price %}
            <SpotPrice>{{ launch_configuration.spot_price }}</SpotPrice>
          {% endif %}
          {% if launch_configuration.metadata_options %}
          <MetadataOptions>
            <HttpTokens>{{ launch_configuration.metadata_options.get("HttpTokens") }}</HttpTokens>
            <HttpPutResponseHopLimit>{{ launch_configuration.metadata_options.get("HttpPutResponseHopLimit") }}</HttpPutResponseHopLimit>
            <HttpEndpoint>{{ launch_configuration.metadata_options.get("HttpEndpoint") }}</HttpEndpoint>
          </MetadataOptions>
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
            <PropagateAtLaunch>{{ 'true' if tag.get("PropagateAtLaunch") else 'false' }}</PropagateAtLaunch>
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
        <CreatedTime>{{ group.created_time }}</CreatedTime>
        {% if group.launch_config_name %}
        <LaunchConfigurationName>{{ group.launch_config_name }}</LaunchConfigurationName>
        {% elif group.mixed_instances_policy %}
        <MixedInstancesPolicy>
          <LaunchTemplate>
            <LaunchTemplateSpecification>
              <LaunchTemplateId>{{ group.launch_template.id }}</LaunchTemplateId>
              <Version>{{ group.launch_template_version }}</Version>
              <LaunchTemplateName>{{ group.launch_template.name }}</LaunchTemplateName>
            </LaunchTemplateSpecification>
            {% if group.mixed_instances_policy.get("LaunchTemplate", {}).get("Overrides", []) %}
            <Overrides>
              {% for member in group.mixed_instances_policy.get("LaunchTemplate", {}).get("Overrides", []) %}
              <member>
                {% if member.get("InstanceType") %}
                <InstanceType>{{ member.get("InstanceType") }}</InstanceType>
                {% endif %}
                {% if member.get("WeightedCapacity") %}
                <WeightedCapacity>{{ member.get("WeightedCapacity") }}</WeightedCapacity>
                {% endif %}
              </member>
              {% endfor %}
            </Overrides>
            {% endif %}
          </LaunchTemplate>
          {% if group.mixed_instances_policy.get("InstancesDistribution") %}
          <InstancesDistribution>
            {% if group.mixed_instances_policy.get("InstancesDistribution").get("OnDemandAllocationStrategy") %}
            <OnDemandAllocationStrategy>{{ group.mixed_instances_policy.get("InstancesDistribution").get("OnDemandAllocationStrategy") }}</OnDemandAllocationStrategy>
            {% endif %}
            {% if group.mixed_instances_policy.get("InstancesDistribution").get("OnDemandBaseCapacity") %}
            <OnDemandBaseCapacity>{{ group.mixed_instances_policy.get("InstancesDistribution").get("OnDemandBaseCapacity") }}</OnDemandBaseCapacity>
            {% endif %}
            {% if group.mixed_instances_policy.get("InstancesDistribution").get("OnDemandPercentageAboveBaseCapacity") %}
            <OnDemandPercentageAboveBaseCapacity>{{ group.mixed_instances_policy.get("InstancesDistribution").get("OnDemandPercentageAboveBaseCapacity") }}</OnDemandPercentageAboveBaseCapacity>
            {% endif %}
            {% if group.mixed_instances_policy.get("InstancesDistribution").get("SpotAllocationStrategy") %}
            <SpotAllocationStrategy>{{ group.mixed_instances_policy.get("InstancesDistribution").get("SpotAllocationStrategy") }}</SpotAllocationStrategy>
            {% endif %}
            {% if group.mixed_instances_policy.get("InstancesDistribution").get("SpotInstancePools") %}
            <SpotInstancePools>{{ group.mixed_instances_policy.get("InstancesDistribution").get("SpotInstancePools") }}</SpotInstancePools>
            {% endif %}
            {% if group.mixed_instances_policy.get("InstancesDistribution").get("SpotMaxPrice") %}
            <SpotMaxPrice>{{ group.mixed_instances_policy.get("InstancesDistribution").get("SpotMaxPrice") }}</SpotMaxPrice>
            {% endif %}
          </InstancesDistribution>
          {% endif %}
        </MixedInstancesPolicy>
        {% elif group.launch_template %}
        <LaunchTemplate>
          <LaunchTemplateId>{{ group.launch_template.id }}</LaunchTemplateId>
          {% if group.provided_launch_template_version %}}
          <Version>{{ group.provided_launch_template_version }}</Version>
          {% endif %}
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
        <CapacityRebalance>{{ 'true' if group.capacity_rebalance else 'false' }}</CapacityRebalance>
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
        <AutoScalingGroupARN>{{ group.arn }}</AutoScalingGroupARN>
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
        {% if group.metrics %}
        <EnabledMetrics>
          {% for met in group.metrics %}
          <member>
          <Metric>{{ met }}</Metric>
          <Granularity>1Minute</Granularity>
          </member>
          {% endfor %}
        </EnabledMetrics>
        {% endif %}
        <ServiceLinkedRoleARN>{{ group.service_linked_role }}</ServiceLinkedRoleARN>
        {% if group.warm_pool %}
        <WarmPoolConfiguration>
          <MaxGroupPreparedCapacity>{{ group.warm_pool.max_group_prepared_capacity }}</MaxGroupPreparedCapacity>
          <MinSize>{{ group.warm_pool.min_size or 0 }}</MinSize>
          {% if group.warm_pool.pool_state %}
          <PoolState>{{ group.warm_pool.pool_state }}</PoolState>
          {% endif %}
          <InstanceReusePolicy>
            <ReuseOnScaleIn>{{ 'true' if group.warm_pool.instance_reuse_policy["ReuseOnScaleIn"] else 'false' }}</ReuseOnScaleIn>
          </InstanceReusePolicy>
        </WarmPoolConfiguration>
        {% endif %}
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


DESCRIBE_LIFECYCLE_HOOKS_TEMPLATE = """<DescribeLifecycleHooksResponse xmlns="http://autoscaling.amazonaws.com/doc/2011-01-01/">
  <DescribeLifecycleHooksResult>
    <LifecycleHooks>
      {% for lifecycle_hook in lifecycle_hooks %}
        <member>
          <AutoScalingGroupName>{{ lifecycle_hook.as_name }}</AutoScalingGroupName>
          <RoleARN>arn:aws:iam::1234567890:role/my-auto-scaling-role</RoleARN>
          <LifecycleTransition>{{ lifecycle_hook.transition }}</LifecycleTransition>
          <GlobalTimeout>172800</GlobalTimeout>
          <LifecycleHookName>{{ lifecycle_hook.name }}</LifecycleHookName>
          <HeartbeatTimeout>{{ lifecycle_hook.timeout }}</HeartbeatTimeout>
          <DefaultResult>{{ lifecycle_hook.result }}</DefaultResult>
          <NotificationTargetARN>arn:aws:sqs:us-east-1:123456789012:my-queue</NotificationTargetARN>
        </member>
      {% endfor %}
    </LifecycleHooks>
  </DescribeLifecycleHooksResult>
  <ResponseMetadata>
    <RequestId>ec3bffad-b739-11e2-b38d-15fbEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeLifecycleHooksResponse>"""


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
