from moto.core.responses import BaseResponse


class Fleets(BaseResponse):
    def delete_fleets(self):
        fleet_ids = self._get_multi_param("FleetId.")
        terminate_instances = self._get_param("TerminateInstances")
        fleets = self.ec2_backend.delete_fleets(fleet_ids, terminate_instances)
        template = self.response_template(DELETE_FLEETS_TEMPLATE)
        return template.render(fleets=fleets)

    def describe_fleet_instances(self):
        fleet_id = self._get_param("FleetId")

        instances = self.ec2_backend.describe_fleet_instances(fleet_id)
        template = self.response_template(DESCRIBE_FLEET_INSTANCES_TEMPLATE)
        return template.render(fleet_id=fleet_id, instances=instances)

    def describe_fleets(self):
        fleet_ids = self._get_multi_param("FleetIds.")

        requests = self.ec2_backend.describe_fleets(fleet_ids)
        template = self.response_template(DESCRIBE_FLEETS_TEMPLATE)
        rend = template.render(requests=requests)
        return rend

    def create_fleet(self):
        on_demand_options = self._get_multi_param_dict("OnDemandOptions")
        spot_options = self._get_multi_param_dict("SpotOptions")
        target_capacity_specification = self._get_multi_param_dict(
            "TargetCapacitySpecification"
        )
        launch_template_configs = self._get_multi_param("LaunchTemplateConfigs")

        excess_capacity_termination_policy = self._get_param(
            "ExcessCapacityTerminationPolicy"
        )
        replace_unhealthy_instances = self._get_param("ReplaceUnhealthyInstances")
        terminate_instances_with_expiration = self._get_param(
            "TerminateInstancesWithExpiration", if_none=True
        )
        fleet_type = self._get_param("Type", if_none="maintain")
        valid_from = self._get_param("ValidFrom")
        valid_until = self._get_param("ValidUntil")

        tag_specifications = self._get_multi_param("TagSpecification")

        request = self.ec2_backend.create_fleet(
            on_demand_options=on_demand_options,
            spot_options=spot_options,
            target_capacity_specification=target_capacity_specification,
            launch_template_configs=launch_template_configs,
            excess_capacity_termination_policy=excess_capacity_termination_policy,
            replace_unhealthy_instances=replace_unhealthy_instances,
            terminate_instances_with_expiration=terminate_instances_with_expiration,
            fleet_type=fleet_type,
            valid_from=valid_from,
            valid_until=valid_until,
            tag_specifications=tag_specifications,
        )

        template = self.response_template(CREATE_FLEET_TEMPLATE)
        return template.render(request=request)


CREATE_FLEET_TEMPLATE = """<CreateFleetResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
    <requestId>60262cc5-2bd4-4c8d-98ed-example</requestId>
    <fleetId>{{ request.id }}</fleetId>
</CreateFleetResponse>"""

DESCRIBE_FLEETS_TEMPLATE = """<DescribeFleetsResponse xmlns="http://ec2.amazonaws.com/doc/2016-09-15/">
    <requestId>4d68a6cc-8f2e-4be1-b425-example</requestId>
    <fleetSet>
        {% for request in requests %}
        <item>
            <fleetId>{{ request.id }}</fleetId>
            <fleetState>{{ request.state }}</fleetState>
            <excessCapacityTerminationPolicy>{{ request.excess_capacity_termination_policy }}</excessCapacityTerminationPolicy>
            <fulfilledCapacity>{{ request.fulfilled_capacity }}</fulfilledCapacity>
            <fulfilledOnDemandCapacity>{{ request.fulfilled_on_demand_capacity }}</fulfilledOnDemandCapacity>
            <launchTemplateConfigs>
                {% for config in request.launch_template_configs %}
                <item>
                    <launchTemplateSpecification>
                        <launchTemplateId>{{ config.LaunchTemplateSpecification.LaunchTemplateId }}</launchTemplateId>
                        <version>{{ config.LaunchTemplateSpecification.Version }}</version>
                    </launchTemplateSpecification>
                </item>
                {% endfor %}
            </launchTemplateConfigs>
            <targetCapacitySpecification>
                <totalTargetCapacity>{{ request.target_capacity }}</totalTargetCapacity>
                {% if request.on_demand_target_capacity %}
                <onDemandTargetCapacity>{{ request.on_demand_target_capacity }}</onDemandTargetCapacity>
                {% endif %}
                {% if request.spot_target_capacity %}
                <spotTargetCapacity>{{ request.spot_target_capacity }}</spotTargetCapacity>
                {% endif %}
                <defaultTargetCapacityType>{{ request.target_capacity_specification.DefaultTargetCapacityType }}</defaultTargetCapacityType>
            </targetCapacitySpecification>
            {% if request.spot_options %}
            <spotOptions>
                {% if request.spot_options.AllocationStrategy %}
                <allocationStrategy>{{ request.spot_options.AllocationStrategy }}</allocationStrategy>
                {% endif %}
                {% if request.spot_options.InstanceInterruptionBehavior %}
                <instanceInterruptionBehavior>{{ request.spot_options.InstanceInterruptionBehavior }}</instanceInterruptionBehavior>
                {% endif %}
                {% if request.spot_options.InstancePoolsToUseCount %}
                <instancePoolsToUseCount>{{ request.spot_options.InstancePoolsToUseCount }}</instancePoolsToUseCount>
                {% endif %}
            </spotOptions>
            {% endif %}
            {% if request.on_demand_options %}
            <onDemandOptions>
                {% if request.on_demand_options.AllocationStrategy %}
                <allocationStrategy>{{ request.on_demand_options.AllocationStrategy }}</allocationStrategy>
                {% endif %}
            </onDemandOptions>
            {% endif %}
            <terminateInstancesWithExpiration>{{ request.terminate_instances_with_expiration }}</terminateInstancesWithExpiration>
            <type>{{ request.fleet_type }}</type>
            <validFrom>{{ request.valid_from }}</validFrom>
            <validUntil>{{ request.valid_until }}</validUntil>
            <replaceUnhealthyInstances>{{ request.replace_unhealthy_instances }}</replaceUnhealthyInstances>
            <tagSet>
                {% for tag in request.tags %}
                <item>
                    <key>{{ tag.key }}</key>
                    <value>{{ tag.value }}</value>
                </item>
                {% endfor %}
            </tagSet>
        </item>
        {% endfor %}
    </fleetSet>
</DescribeFleetsResponse>"""

DESCRIBE_FLEET_INSTANCES_TEMPLATE = """<DescribeFleetInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2016-09-15/">
    <requestId>cfb09950-45e2-472d-a6a9-example</requestId>
    <spotFleetRequestId>{{ fleet_id }}</spotFleetRequestId>
    <activeInstanceSet>
        {% for i in instances %}
        <item>
            <instanceId>{{ i.instance.id }}</instanceId>
            {% if i.sir_id %}
            <spotInstanceRequestId>{{ i.id }}</spotInstanceRequestId>
            {% endif %}
            <instanceType>{{ i.instance.instance_type }}</instanceType>
        </item>
        {% endfor %}
    </activeInstanceSet>
</DescribeFleetInstancesResponse>
"""

DELETE_FLEETS_TEMPLATE = """<DeleteFleetResponse xmlns="http://ec2.amazonaws.com/doc/2016-09-15/">
    <requestId>e12d2fe5-6503-4b4b-911c-example</requestId>
    <unsuccessfulFleetDeletionSet/>
    <successfulFleetDeletionSet>
        {% for fleet in fleets %}
        <item>
            <fleetId>{{ fleet.id }}</fleetId>
            <currentFleetState>{{ fleet.state }}</currentFleetState>
            <previousFleetState>active</previousFleetState>
        </item>
        {% endfor %}
    </successfulFleetDeletionSet>
</DeleteFleetResponse>"""
