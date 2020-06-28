from __future__ import unicode_literals
from moto.core import BaseBackend, BaseModel
from moto.ecs import ecs_backends
from .exceptions import AWSValidationException
from collections import OrderedDict
from enum import Enum, unique
import time


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


class ApplicationAutoscalingBackend(BaseBackend):
    def __init__(self, region, ecs):
        super(ApplicationAutoscalingBackend, self).__init__()
        self.region = region
        self.ecs_backend = ecs
        self.targets = OrderedDict()

    def reset(self):
        region = self.region
        ecs = self.ecs_backend
        self.__dict__ = {}
        self.__init__(region, ecs)

    @property
    def applicationautoscaling_backend(self):
        return applicationautoscaling_backends[self.region]

    def describe_scalable_targets(
        self, namespace, r_ids=None, dimension=None,
    ):
        """ Describe scalable targets. """
        if r_ids is None:
            r_ids = []
        targets = self._flatten_scalable_targets(namespace)
        if dimension is not None:
            targets = [t for t in targets if t.scalable_dimension == dimension]
        if len(r_ids) > 0:
            targets = [t for t in targets if t.resource_id in r_ids]
        return targets

    def _flatten_scalable_targets(self, namespace):
        """ Flatten scalable targets for a given service namespace down to a list. """
        targets = []
        for dimension in self.targets.keys():
            for resource_id in self.targets[dimension].keys():
                targets.append(self.targets[dimension][resource_id])
        targets = [t for t in targets if t.service_namespace == namespace]
        return targets

    def register_scalable_target(self, namespace, r_id, dimension, **kwargs):
        """ Registers or updates a scalable target. """
        _ = _target_params_are_valid(namespace, r_id, dimension)
        if namespace == ServiceNamespaceValueSet.ECS.value:
            _ = self._ecs_service_exists_for_target(r_id)
        if self._scalable_target_exists(r_id, dimension):
            target = self.targets[dimension][r_id]
            target.update(kwargs)
        else:
            target = FakeScalableTarget(self, namespace, r_id, dimension, **kwargs)
            self._add_scalable_target(target)
        return target

    def _scalable_target_exists(self, r_id, dimension):
        return r_id in self.targets.get(dimension, [])

    def _ecs_service_exists_for_target(self, r_id):
        """ Raises a ValidationException if an ECS service does not exist
            for the specified resource ID.
        """
        resource_type, cluster, service = r_id.split("/")
        result = self.ecs_backend.describe_services(cluster, [service])
        if len(result) != 1:
            raise AWSValidationException("ECS service doesn't exist: {}".format(r_id))
        return True

    def _add_scalable_target(self, target):
        if target.scalable_dimension not in self.targets:
            self.targets[target.scalable_dimension] = OrderedDict()
        if target.resource_id not in self.targets[target.scalable_dimension]:
            self.targets[target.scalable_dimension][target.resource_id] = target
        return target


def _target_params_are_valid(namespace, r_id, dimension):
    """ Check whether namespace, resource_id and dimension are valid and consistent with each other. """
    is_valid = True
    valid_namespaces = [n.value for n in ServiceNamespaceValueSet]
    if namespace not in valid_namespaces:
        is_valid = False
    if dimension is not None:
        try:
            valid_dimensions = [d.value for d in ScalableDimensionValueSet]
            d_namespace, d_resource_type, scaling_property = dimension.split(":")
            resource_type, cluster, service = r_id.split("/")
            if (
                dimension not in valid_dimensions
                or d_namespace != namespace
                or resource_type != d_resource_type
            ):
                is_valid = False
        except ValueError:
            is_valid = False
    if not is_valid:
        raise AWSValidationException(
            "Unsupported service namespace, resource type or scalable dimension"
        )
    return is_valid


class FakeScalableTarget(BaseModel):
    def __init__(
        self, backend, service_namespace, resource_id, scalable_dimension, **kwargs
    ):
        self.applicationautoscaling_backend = backend
        self.service_namespace = service_namespace
        self.resource_id = resource_id
        self.scalable_dimension = scalable_dimension
        self.min_capacity = kwargs["min_capacity"]
        self.max_capacity = kwargs["max_capacity"]
        self.role_arn = kwargs["role_arn"]
        self.suspended_state = kwargs["suspended_state"]
        self.creation_time = time.time()

    def update(self, **kwargs):
        if kwargs["min_capacity"] is not None:
            self.min_capacity = kwargs["min_capacity"]
        if kwargs["max_capacity"] is not None:
            self.max_capacity = kwargs["max_capacity"]


applicationautoscaling_backends = {}
for region_name, ecs_backend in ecs_backends.items():
    applicationautoscaling_backends[region_name] = ApplicationAutoscalingBackend(
        region_name, ecs_backend
    )
