"""Handles incoming codedeploy requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import (
    Application,
    CodeDeployBackend,
    DeploymentGroup,
    DeploymentInfo,
    codedeploy_backends,
)


def _application_info(application: Application) -> dict[str, Any]:
    return {
        "applicationId": application.id,
        "applicationName": application.application_name,
        "createTime": application.create_time,
        "computePlatform": application.compute_platform,
    }


def _deployment_group_info(deployment_group: DeploymentGroup) -> dict[str, Any]:
    return {
        "applicationName": deployment_group.application.application_name,
        "deploymentGroupId": deployment_group.deployment_group_id,
        "deploymentGroupName": deployment_group.deployment_group_name,
        "deploymentConfigName": str(deployment_group.deployment_config_name),
        "ec2TagFilters": deployment_group.ec2_tag_filters,
        "onPremisesInstanceTagFilters": deployment_group.on_premises_instance_tag_filters,
        "autoScalingGroups": deployment_group.auto_scaling_groups,
        "serviceRoleArn": deployment_group.service_role_arn,
        "targetRevision": {},  # TODO
        "triggerConfigurations": deployment_group.trigger_configurations,
        "alarmConfiguration": {},  # TODO
        "autoRollbackConfiguration": deployment_group.auto_rollback_configuration,
        "deploymentStyle": deployment_group.deployment_style,
        "outdatedInstancesStrategy": deployment_group.outdated_instances_strategy,
        "blueGreenDeploymentConfiguration": deployment_group.blue_green_deployment_configuration,
        "loadBalancerInfo": deployment_group.load_balancer_info,
        "lastSuccessfulDeployment": {},  # TODO
        "lastAttemptedDeployment": {},  # TODO
        "ec2TagSet": deployment_group.ec2_tag_set,
        "onPremisesTagSet": deployment_group.on_premises_tag_set,
        "computePlatform": deployment_group.application.compute_platform,
        "ecsServices": deployment_group.ecs_services,
        "terminationHookEnabled": deployment_group.termination_hook_enabled,
    }


def _deployment_info(deployment: DeploymentInfo) -> dict[str, Any]:
    deployment_group = deployment.deployment_group
    return {
        "applicationName": deployment.application_name,
        "deploymentGroupName": deployment.deployment_group_name,
        "deploymentConfigName": str(deployment.deployment_config_name),
        "deploymentId": deployment.deployment_id,
        "previousRevision": {},  # TODO
        "revision": deployment.revision,
        "status": deployment.status,
        "errorInformation": {},  # TODO
        "createTime": deployment.create_time,
        "startTime": deployment.start_time,
        "completeTime": deployment.complete_time,
        "deploymentOverview": deployment.deployment_overview,
        "description": deployment.description,
        "creator": deployment.creator,
        "ignoreApplicationStopFailures": deployment.ignore_application_stop_failures,
        "autoRollbackConfiguration": deployment.auto_rollback_configuration,
        "updateOutdatedInstancesOnly": deployment.update_outdated_instances_only,
        "rollbackInfo": {},  # TODO information about a deployment rollback
        "deploymentStyle": deployment_group.deployment_style,
        "targetInstances": deployment.target_instances,
        "instanceTerminationWaitTimeStarted": deployment.instance_termination_wait_time_started,  # TODO
        "blueGreenDeploymentConfiguration": deployment_group.blue_green_deployment_configuration,
        "loadBalancerInfo": deployment_group.load_balancer_info,
        "additionalDeploymentStatusInfo": deployment.additional_deployment_status_info,  # TODO
        "fileExistsBehavior": deployment.file_exists_behavior,
        "deploymentStatusMessages": deployment.deployment_status_messages,  # TODO
        "computePlatform": deployment.application.compute_platform,
        "externalId": deployment.external_id,
        "relatedDeployments": deployment.related_deployments,  # TODO
        "overrideAlarmConfiguration": deployment.override_alarm_configuration,
    }


class CodeDeployResponse(BaseResponse):
    """Handler for CodeDeploy requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="codedeploy")
        self.automated_parameter_parsing = True

    @property
    def codedeploy_backend(self) -> CodeDeployBackend:
        """Return backend instance specific for this region."""
        return codedeploy_backends[self.current_account][self.region]

    def batch_get_applications(self) -> ActionResult:
        application_names = self._get_param("applicationNames")
        applications = self.codedeploy_backend.batch_get_applications(
            application_names=application_names,
        )
        result = {"applicationsInfo": [_application_info(app) for app in applications]}
        return ActionResult(result)

    def get_application(self) -> ActionResult:
        application_name = self._get_param("applicationName")
        application = self.codedeploy_backend.get_application(
            application_name=application_name,
        )
        return ActionResult({"application": _application_info(application)})

    def get_deployment(self) -> ActionResult:
        deployment_id = self._get_param("deploymentId")
        deployment = self.codedeploy_backend.get_deployment(
            deployment_id=deployment_id,
        )
        return ActionResult({"deploymentInfo": _deployment_info(deployment)})

    def get_deployment_group(self) -> ActionResult:
        application_name = self._get_param("applicationName")
        deployment_group_name = self._get_param("deploymentGroupName")
        deployment_group = self.codedeploy_backend.get_deployment_group(
            application_name=application_name,
            deployment_group_name=deployment_group_name,
        )
        result = {"deploymentGroupInfo": _deployment_group_info(deployment_group)}
        return ActionResult(result)

    def batch_get_deployments(self) -> ActionResult:
        deployment_ids = self._get_param("deploymentIds")
        deployments = self.codedeploy_backend.batch_get_deployments(
            deployment_ids=deployment_ids,
        )
        result = {
            "deploymentsInfo": [
                _deployment_info(deployment) for deployment in deployments
            ]
        }
        return ActionResult(result)

    def create_application(self) -> ActionResult:
        application_name = self._get_param("applicationName")
        compute_platform = self._get_param("computePlatform")
        tags = self._get_param("tags")
        application_id = self.codedeploy_backend.create_application(
            application_name=application_name,
            compute_platform=compute_platform,
            tags=tags,
        )
        return ActionResult({"applicationId": application_id})

    def create_deployment(self) -> ActionResult:
        application_name = self._get_param("applicationName")
        deployment_group_name = self._get_param("deploymentGroupName")
        revision = self._get_param("revision")
        deployment_config_name = self._get_param("deploymentConfigName")
        description = self._get_param("description")
        ignore_application_stop_failures = self._get_bool_param(
            "ignoreApplicationStopFailures"
        )
        target_instances = self._get_param("targetInstances")
        auto_rollback_configuration = self._get_param("autoRollbackConfiguration")
        update_outdated_instances_only = self._get_bool_param(
            "updateOutdatedInstancesOnly"
        )
        file_exists_behavior = self._get_param("fileExistsBehavior")
        override_alarm_configuration = self._get_param("overrideAlarmConfiguration")
        deployment_id = self.codedeploy_backend.create_deployment(
            application_name=application_name,
            deployment_group_name=deployment_group_name,
            revision=revision,
            deployment_config_name=deployment_config_name,
            description=description,
            ignore_application_stop_failures=ignore_application_stop_failures,
            target_instances=target_instances,
            auto_rollback_configuration=auto_rollback_configuration,
            update_outdated_instances_only=update_outdated_instances_only,
            file_exists_behavior=file_exists_behavior,
            override_alarm_configuration=override_alarm_configuration,
        )
        return ActionResult({"deploymentId": deployment_id})

    def create_deployment_group(self) -> ActionResult:
        application_name = self._get_param("applicationName")
        deployment_group_name = self._get_param("deploymentGroupName")
        deployment_config_name = self._get_param("deploymentConfigName")
        ec2_tag_filters = self._get_param("ec2TagFilters")
        on_premises_instance_tag_filters = self._get_param(
            "onPremisesInstanceTagFilters"
        )
        auto_scaling_groups = self._get_param("autoScalingGroups")
        service_role_arn = self._get_param("serviceRoleArn")
        trigger_configurations = self._get_param("triggerConfigurations")
        alarm_configuration = self._get_param("alarmConfiguration")
        auto_rollback_configuration = self._get_param("autoRollbackConfiguration")
        outdated_instances_strategy = self._get_param("outdatedInstancesStrategy")
        deployment_style = self._get_param("deploymentStyle")
        blue_green_deployment_configuration = self._get_param(
            "blueGreenDeploymentConfiguration"
        )
        load_balancer_info = self._get_param("loadBalancerInfo")
        ec2_tag_set = self._get_param("ec2TagSet")
        ecs_services = self._get_param("ecsServices")
        on_premises_tag_set = self._get_param("onPremisesTagSet")
        tags = self._get_param("tags")
        termination_hook_enabled = self._get_bool_param("terminationHookEnabled")
        deployment_group_id = self.codedeploy_backend.create_deployment_group(
            application_name=application_name,
            deployment_group_name=deployment_group_name,
            deployment_config_name=deployment_config_name,
            ec2_tag_filters=ec2_tag_filters,
            on_premises_instance_tag_filters=on_premises_instance_tag_filters,
            auto_scaling_groups=auto_scaling_groups,
            service_role_arn=service_role_arn,
            trigger_configurations=trigger_configurations,
            alarm_configuration=alarm_configuration,
            auto_rollback_configuration=auto_rollback_configuration,
            outdated_instances_strategy=outdated_instances_strategy,
            deployment_style=deployment_style,
            blue_green_deployment_configuration=blue_green_deployment_configuration,
            load_balancer_info=load_balancer_info,
            ec2_tag_set=ec2_tag_set,
            ecs_services=ecs_services,
            on_premises_tag_set=on_premises_tag_set,
            tags=tags,
            termination_hook_enabled=termination_hook_enabled,
        )
        return ActionResult({"deploymentGroupId": deployment_group_id})

    def list_applications(self) -> ActionResult:
        applications = self.codedeploy_backend.list_applications()
        return ActionResult({"applications": applications})

    def list_deployments(self) -> ActionResult:
        application_name = self._get_param("applicationName")
        deployment_group_name = self._get_param("deploymentGroupName")
        external_id = self._get_param("externalId")
        include_only_statuses = self._get_param("includeOnlyStatuses")
        create_time_range = self._get_param("createTimeRange")
        deployments = self.codedeploy_backend.list_deployments(
            application_name=application_name,
            deployment_group_name=deployment_group_name,
            external_id=external_id,
            include_only_statuses=include_only_statuses,
            create_time_range=create_time_range,
        )
        return ActionResult({"deployments": deployments})

    def list_deployment_groups(self) -> ActionResult:
        application_name = self._get_param("applicationName")
        next_token = self._get_param("nextToken", "")
        deployment_groups = self.codedeploy_backend.list_deployment_groups(
            application_name=application_name,
            next_token=next_token,
        )
        result = {
            "applicationName": application_name,
            "deploymentGroups": deployment_groups,
            "nextToken": next_token,
        }
        return ActionResult(result)

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self.codedeploy_backend.list_tags_for_resource(resource_arn)
        return ActionResult({"Tags": tags})

    def tag_resource(self) -> EmptyResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        self.codedeploy_backend.tag_resource(
            resource_arn, {tag["Key"]: tag.get("Value", "") for tag in tags}
        )
        return EmptyResult()

    def untag_resource(self) -> EmptyResult:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagKeys")
        self.codedeploy_backend.untag_resource(resource_arn, tag_keys)
        return EmptyResult()
