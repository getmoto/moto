from __future__ import unicode_literals
from moto.core.responses import BaseResponse
import json
from .models import applicationautoscaling_backends
from .exceptions import AWSValidationException
from enum import Enum, unique


@unique
class ServiceNamespaceValueSet(Enum):
    APPSTREAM = "appstream"
    RDS = "rds"
    LAMBDA = "lambda"
    CASSANDRA = "cassandra"
    DYNAMODB = "dynamodb"
    CUSTOM_RESOURCE = "custom-resource"
    ELASTICMAPREDUCE = "elasticmapreduce"
    EC2 = "ec2"
    COMPREHEND = "comprehend"
    ECS = "ecs"
    SAGEMAKER = "sagemaker"


@unique
class ScalableDimensionValueSet(Enum):
    CASSANDRA_TABLE_READ_CAPACITY_UNITS = "cassandra:table:ReadCapacityUnits"
    CASSANDRA_TABLE_WRITE_CAPACITY_UNITS = "cassandra:table:WriteCapacityUnits"
    DYNAMODB_INDEX_READ_CAPACITY_UNITS = "dynamodb:index:ReadCapacityUnits"
    DYNAMODB_INDEX_WRITE_CAPACITY_UNITS = "dynamodb:index:WriteCapacityUnits"
    DYNAMODB_TABLE_READ_CAPACITY_UNITS = "dynamodb:table:ReadCapacityUnits"
    DYNAMODB_TABLE_WRITE_CAPACITY_UNITS = "dynamodb:table:WriteCapacityUnits"
    RDS_CLUSTER_READ_REPLICA_COUNT = "rds:cluster:ReadReplicaCount"
    RDS_CLUSTER_CAPACITY = "rds:cluster:Capacity"
    COMPREHEND_DOCUMENT_CLASSIFIER_ENDPOINT_DESIRED_INFERENCE_UNITS = (
        "comprehend:document-classifier-endpoint:DesiredInferenceUnits"
    )
    ELASTICMAPREDUCE_INSTANCE_FLEET_ON_DEMAND_CAPACITY = (
        "elasticmapreduce:instancefleet:OnDemandCapacity"
    )
    ELASTICMAPREDUCE_INSTANCE_FLEET_SPOT_CAPACITY = (
        "elasticmapreduce:instancefleet:SpotCapacity"
    )
    ELASTICMAPREDUCE_INSTANCE_GROUP_INSTANCE_COUNT = (
        "elasticmapreduce:instancegroup:InstanceCount"
    )
    LAMBDA_FUNCTION_PROVISIONED_CONCURRENCY = "lambda:function:ProvisionedConcurrency"
    APPSTREAM_FLEET_DESIRED_CAPACITY = "appstream:fleet:DesiredCapacity"
    CUSTOM_RESOURCE_RESOURCE_TYPE_PROPERTY = "custom-resource:ResourceType:Property"
    SAGEMAKER_VARIANT_DESIRED_INSTANCE_COUNT = "sagemaker:variant:DesiredInstanceCount"
    EC2_SPOT_FLEET_REQUEST_TARGET_CAPACITY = "ec2:spot-fleet-request:TargetCapacity"
    ECS_SERVICE_DESIRED_COUNT = "ecs:service:DesiredCount"


class ApplicationAutoScalingResponse(BaseResponse):
    @property
    def applicationautoscaling_backend(self):
        return applicationautoscaling_backends[self.region]

    def delete_scaling_policy(self):
        """ Not yet implemented. """
        pass

    def delete_scheduled_action(self):
        """ Not yet implemented. """
        pass

    def deregister_scalable_target(self):
        """ Not yet implemented. """
        pass

    def describe_scalable_targets(self):
        validation = self._validate_params()
        if validation is not None:
            return validation
        service_namespace = self._get_param("ServiceNamespace")
        resource_ids = self._get_param("ResourceIds")
        scalable_dimension = self._get_param("ScalableDimension")
        max_results = self._get_int_param("MaxResults", 50)
        marker = self._get_param("NextToken")
        all_scalable_targets = self.applicationautoscaling_backend.describe_scalable_targets(
            service_namespace, resource_ids, scalable_dimension, max_results
        )
        start = int(marker) + 1 if marker else 0
        next_token = None
        scalable_targets_resp = all_scalable_targets[start : start + max_results]
        if len(all_scalable_targets) > start + max_results:
            next_token = str(len(scalable_targets_resp) - 1)
        targets = [
            {
                # TODO Implement CreationTime support
                # "CreationTime": t.creation_time,
                "ServiceNamespace": t.service_namespace,
                "ResourceId": t.resource_id,
                "RoleARN": t.role_arn,
                "ScalableDimension": t.scalable_dimension,
                "MaxCapacity": t.max_capacity,
                "MinCapacity": t.min_capacity,
                # TODO Implement SuspendedState support
                # "SuspendedState": {
                #     "DynamicScalingInSuspended": t.suspended_state["dynamic_scaling_in_suspended"],
                #     "DynamicScalingOutSuspended": t.suspended_state["dynamic_scaling_out_suspended"],
                #     "ScheduledScalingSuspended": t.suspended_state["scheduled_scaling_suspended"],
                # }
            }
            for t in scalable_targets_resp
        ]
        return json.dumps({"ScalableTargets": targets, "NextToken": next_token})

    def describe_scaling_activities(self):
        """ Not yet implemented. """
        pass

    def describe_scaling_policies(self):
        """ Not yet implemented. """
        pass

    def describe_scheduled_actions(self):
        """ Not yet implemented. """
        pass

    def generate_presigned_url(self):
        """ Not yet implemented. """
        pass

    def get_waiter(self):
        """ Not yet implemented. """
        pass

    def put_scaling_policy(self):
        """ Not yet implemented. """
        pass

    def put_scheduled_action(self):
        """ Not yet implemented. """
        pass

    def register_scalable_target(self):
        """ Registers or updates a scalable target. """
        validation = self._validate_params()
        if validation is not None:
            return validation
        self.applicationautoscaling_backend.register_scalable_target(
            self._get_param("ServiceNamespace"),
            self._get_param("ResourceId"),
            self._get_param("ScalableDimension"),
            min_capacity=self._get_int_param("MinCapacity"),
            max_capacity=self._get_int_param("MaxCapacity"),
            role_arn=self._get_param("RoleARN"),
            suspended_state=self._get_param("SuspendedState"),
        )
        return json.dumps({})

    def _validate_params(self):
        namespace = self._get_param("ServiceNamespace")
        dimension = self._get_param("ScalableDimension")
        messages = []
        resp = None
        dimensions = [dimension.value for dimension in ScalableDimensionValueSet]
        if dimension is not None and dimension not in dimensions:
            messages.append(
                "Value '{}' at 'scalableDimension' "
                "failed to satisfy constraint: Member must satisfy enum value set: "
                "{}".format(dimension, dimensions)
            )
        namespaces = [namespace.value for namespace in ServiceNamespaceValueSet]
        if namespace is not None and namespace not in namespaces:
            messages.append(
                "Value '{}' at 'serviceNamespace' "
                "failed to satisfy constraint: Member must satisfy enum value set: "
                "{}".format(namespace, namespaces)
            )
        if len(messages) == 1:
            resp = AWSValidationException(
                "1 validation error detected: {}".format(messages[0])
            ).response()
        elif len(messages) > 1:
            resp = AWSValidationException(
                "{} validation errors detected: {}".format(
                    len(messages), " ;".join(messages)
                )
            ).response()
        return resp
