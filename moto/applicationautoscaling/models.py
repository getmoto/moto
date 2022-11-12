from moto.core import BaseBackend, BackendDict, BaseModel
from moto.ecs import ecs_backends
from moto.moto_api._internal import mock_random
from .exceptions import AWSValidationException
from collections import OrderedDict
from enum import Enum, unique
from typing import Dict, List, Union, Optional, Tuple
import time


@unique
class ResourceTypeExceptionValueSet(Enum):
    RESOURCE_TYPE = "ResourceType"
    # MSK currently only has the "broker-storage" resource type which is not part of the resource_id
    KAFKA_BROKER_STORAGE = "broker-storage"


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
    KAFKA = "kafka"


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
    KAFKA_BROKER_STORAGE_VOLUME_SIZE = "kafka:broker-storage:VolumeSize"


class ApplicationAutoscalingBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.ecs_backend = ecs_backends[account_id][region_name]
        self.targets: Dict[str, Dict[str, FakeScalableTarget]] = OrderedDict()
        self.policies: Dict[str, FakeApplicationAutoscalingPolicy] = {}
        self.scheduled_actions: List[FakeScheduledAction] = list()

    @staticmethod
    def default_vpc_endpoint_service(
        service_region: str, zones: List[str]
    ) -> List[Dict[str, str]]:
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "application-autoscaling"
        )

    def describe_scalable_targets(
        self, namespace: str, r_ids: Union[None, List[str]], dimension: Union[None, str]
    ) -> List["FakeScalableTarget"]:
        """Describe scalable targets."""
        if r_ids is None:
            r_ids = []
        targets = self._flatten_scalable_targets(namespace)
        if dimension is not None:
            targets = [t for t in targets if t.scalable_dimension == dimension]
        if len(r_ids) > 0:
            targets = [t for t in targets if t.resource_id in r_ids]
        return targets

    def _flatten_scalable_targets(self, namespace: str) -> List["FakeScalableTarget"]:
        """Flatten scalable targets for a given service namespace down to a list."""
        targets = []
        for dimension in self.targets.keys():
            for resource_id in self.targets[dimension].keys():
                targets.append(self.targets[dimension][resource_id])
        targets = [t for t in targets if t.service_namespace == namespace]
        return targets

    def register_scalable_target(
        self,
        namespace: str,
        r_id: str,
        dimension: str,
        min_capacity: Optional[int],
        max_capacity: Optional[int],
        role_arn: str,
        suspended_state: str,
    ) -> "FakeScalableTarget":
        """Registers or updates a scalable target."""
        _ = _target_params_are_valid(namespace, r_id, dimension)
        if namespace == ServiceNamespaceValueSet.ECS.value:
            _ = self._ecs_service_exists_for_target(r_id)
        if self._scalable_target_exists(r_id, dimension):
            target = self.targets[dimension][r_id]
            target.update(min_capacity, max_capacity, suspended_state)
        else:
            target = FakeScalableTarget(
                self,
                namespace,
                r_id,
                dimension,
                min_capacity,
                max_capacity,
                role_arn,
                suspended_state,
            )
            self._add_scalable_target(target)
        return target

    def _scalable_target_exists(self, r_id: str, dimension: str) -> bool:
        return r_id in self.targets.get(dimension, [])

    def _ecs_service_exists_for_target(self, r_id: str) -> bool:
        """Raises a ValidationException if an ECS service does not exist
        for the specified resource ID.
        """
        _, cluster, service = r_id.split("/")
        result, _ = self.ecs_backend.describe_services(cluster, [service])
        if len(result) != 1:
            raise AWSValidationException(f"ECS service doesn't exist: {r_id}")
        return True

    def _add_scalable_target(
        self, target: "FakeScalableTarget"
    ) -> "FakeScalableTarget":
        if target.scalable_dimension not in self.targets:
            self.targets[target.scalable_dimension] = OrderedDict()
        if target.resource_id not in self.targets[target.scalable_dimension]:
            self.targets[target.scalable_dimension][target.resource_id] = target
        return target

    def deregister_scalable_target(
        self, namespace: str, r_id: str, dimension: str
    ) -> None:
        """Registers or updates a scalable target."""
        if self._scalable_target_exists(r_id, dimension):
            del self.targets[dimension][r_id]
        else:
            raise AWSValidationException(
                f"No scalable target found for service namespace: {namespace}, resource ID: {r_id}, scalable dimension: {dimension}"
            )

    def put_scaling_policy(
        self,
        policy_name: str,
        service_namespace: str,
        resource_id: str,
        scalable_dimension: str,
        policy_body: str,
        policy_type: Optional[None],
    ) -> "FakeApplicationAutoscalingPolicy":
        policy_key = FakeApplicationAutoscalingPolicy.formulate_key(
            service_namespace, resource_id, scalable_dimension, policy_name
        )
        if policy_key in self.policies:
            old_policy = self.policies[policy_key]
            policy = FakeApplicationAutoscalingPolicy(
                region_name=self.region_name,
                policy_name=policy_name,
                service_namespace=service_namespace,
                resource_id=resource_id,
                scalable_dimension=scalable_dimension,
                policy_type=policy_type if policy_type else old_policy.policy_type,
                policy_body=policy_body if policy_body else old_policy._policy_body,
            )
        else:
            policy = FakeApplicationAutoscalingPolicy(
                region_name=self.region_name,
                policy_name=policy_name,
                service_namespace=service_namespace,
                resource_id=resource_id,
                scalable_dimension=scalable_dimension,
                policy_type=policy_type,
                policy_body=policy_body,
            )
        self.policies[policy_key] = policy
        return policy

    def describe_scaling_policies(
        self,
        service_namespace: str,
        resource_id: str,
        scalable_dimension: str,
        max_results: Optional[int],
        next_token: str,
    ) -> Tuple[Optional[str], List["FakeApplicationAutoscalingPolicy"]]:
        max_results = max_results or 100
        policies = [
            policy
            for policy in self.policies.values()
            if policy.service_namespace == service_namespace
        ]
        if resource_id:
            policies = [
                policy for policy in policies if policy.resource_id in resource_id
            ]
        if scalable_dimension:
            policies = [
                policy
                for policy in policies
                if policy.scalable_dimension in scalable_dimension
            ]
        starting_point = int(next_token) if next_token else 0
        ending_point = starting_point + max_results
        policies_page = policies[starting_point:ending_point]
        new_next_token = str(ending_point) if ending_point < len(policies) else None
        return new_next_token, policies_page

    def delete_scaling_policy(
        self,
        policy_name: str,
        service_namespace: str,
        resource_id: str,
        scalable_dimension: str,
    ) -> None:
        policy_key = FakeApplicationAutoscalingPolicy.formulate_key(
            service_namespace, resource_id, scalable_dimension, policy_name
        )
        if policy_key in self.policies:
            del self.policies[policy_key]
        else:
            raise AWSValidationException(
                f"No scaling policy found for service namespace: {service_namespace}, resource ID: {resource_id}, scalable dimension: {scalable_dimension}, policy name: {policy_name}"
            )

    def delete_scheduled_action(
        self,
        service_namespace: str,
        scheduled_action_name: str,
        resource_id: str,
        scalable_dimension: str,
    ) -> None:
        self.scheduled_actions = [
            a
            for a in self.scheduled_actions
            if not (
                a.service_namespace == service_namespace
                and a.scheduled_action_name == scheduled_action_name
                and a.resource_id == resource_id
                and a.scalable_dimension == scalable_dimension
            )
        ]

    def describe_scheduled_actions(
        self,
        scheduled_action_names: str,
        service_namespace: str,
        resource_id: str,
        scalable_dimension: str,
    ) -> List["FakeScheduledAction"]:
        """
        Pagination is not yet implemented
        """
        result = [
            a
            for a in self.scheduled_actions
            if a.service_namespace == service_namespace
        ]
        if scheduled_action_names:
            result = [
                a for a in result if a.scheduled_action_name in scheduled_action_names
            ]
        if resource_id:
            result = [a for a in result if a.resource_id == resource_id]
        if scalable_dimension:
            result = [a for a in result if a.scalable_dimension == scalable_dimension]
        return result

    def put_scheduled_action(
        self,
        service_namespace: str,
        schedule: str,
        timezone: str,
        scheduled_action_name: str,
        resource_id: str,
        scalable_dimension: str,
        start_time: str,
        end_time: str,
        scalable_target_action: str,
    ) -> None:
        existing_action = next(
            (
                a
                for a in self.scheduled_actions
                if a.service_namespace == service_namespace
                and a.resource_id == resource_id
                and a.scalable_dimension == scalable_dimension
            ),
            None,
        )
        if existing_action:
            existing_action.update(
                schedule,
                timezone,
                scheduled_action_name,
                start_time,
                end_time,
                scalable_target_action,
            )
        else:
            action = FakeScheduledAction(
                service_namespace,
                schedule,
                timezone,
                scheduled_action_name,
                resource_id,
                scalable_dimension,
                start_time,
                end_time,
                scalable_target_action,
                self.account_id,
                self.region_name,
            )
            self.scheduled_actions.append(action)


def _target_params_are_valid(namespace: str, r_id: str, dimension: str) -> bool:
    """Check whether namespace, resource_id and dimension are valid and consistent with each other."""
    is_valid = True
    valid_namespaces = [n.value for n in ServiceNamespaceValueSet]
    if namespace not in valid_namespaces:
        is_valid = False
    if dimension is not None:
        try:
            valid_dimensions = [d.value for d in ScalableDimensionValueSet]
            resource_type_exceptions = [r.value for r in ResourceTypeExceptionValueSet]
            d_namespace, d_resource_type, _ = dimension.split(":")
            if d_resource_type not in resource_type_exceptions:
                resource_type = _get_resource_type_from_resource_id(r_id)
            else:
                resource_type = d_resource_type
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


def _get_resource_type_from_resource_id(resource_id: str) -> str:
    # AWS Application Autoscaling resource_ids are multi-component (path-like) identifiers that vary in format,
    # depending on the type of resource it identifies.  resource_type is one of its components.
    #  resource_id format variations are described in
    #   https://docs.aws.amazon.com/autoscaling/application/APIReference/API_RegisterScalableTarget.html
    #  In a nutshell:
    #  - Most use slash separators, but some use colon separators.
    #  - The resource type is usually the first component of the resource_id...
    #    - ...except for sagemaker endpoints, dynamodb GSIs and keyspaces tables, where it's the third.
    #  - Comprehend uses an arn, with the resource type being the last element.

    if resource_id.startswith("arn:aws:comprehend"):
        resource_id = resource_id.split(":")[-1]
    resource_split = (
        resource_id.split("/") if "/" in resource_id else resource_id.split(":")
    )
    if (
        resource_split[0] == "endpoint"
        or (resource_split[0] == "table" and len(resource_split) > 2)
        or (resource_split[0] == "keyspace")
    ):
        resource_type = resource_split[2]
    else:
        resource_type = resource_split[0]
    return resource_type


class FakeScalableTarget(BaseModel):
    def __init__(
        self,
        backend: ApplicationAutoscalingBackend,
        service_namespace: str,
        resource_id: str,
        scalable_dimension: str,
        min_capacity: Optional[int],
        max_capacity: Optional[int],
        role_arn: str,
        suspended_state: str,
    ) -> None:
        self.applicationautoscaling_backend = backend
        self.service_namespace = service_namespace
        self.resource_id = resource_id
        self.scalable_dimension = scalable_dimension
        self.min_capacity = min_capacity
        self.max_capacity = max_capacity
        self.role_arn = role_arn
        self.suspended_state = suspended_state
        self.creation_time = time.time()

    def update(
        self,
        min_capacity: Optional[int],
        max_capacity: Optional[int],
        suspended_state: str,
    ) -> None:
        if min_capacity is not None:
            self.min_capacity = min_capacity
        if max_capacity is not None:
            self.max_capacity = max_capacity
        if suspended_state is not None:
            self.suspended_state = suspended_state


class FakeApplicationAutoscalingPolicy(BaseModel):
    def __init__(
        self,
        region_name: str,
        policy_name: str,
        service_namespace: str,
        resource_id: str,
        scalable_dimension: str,
        policy_type: Optional[str],
        policy_body: str,
    ) -> None:
        self.step_scaling_policy_configuration = None
        self.target_tracking_scaling_policy_configuration = None

        if policy_type == "StepScaling":
            self.step_scaling_policy_configuration = policy_body
            self.target_tracking_scaling_policy_configuration = None
        elif policy_type == "TargetTrackingScaling":
            self.step_scaling_policy_configuration = None
            self.target_tracking_scaling_policy_configuration = policy_body
        else:
            raise AWSValidationException(
                f"Unknown policy type {policy_type} specified."
            )

        self._policy_body = policy_body
        self.service_namespace = service_namespace
        self.resource_id = resource_id
        self.scalable_dimension = scalable_dimension
        self.policy_name = policy_name
        self.policy_type = policy_type
        self._guid = mock_random.uuid4()
        self.policy_arn = f"arn:aws:autoscaling:{region_name}:scalingPolicy:{self._guid}:resource/{self.service_namespace}/{self.resource_id}:policyName/{self.policy_name}"
        self.creation_time = time.time()

    @staticmethod
    def formulate_key(
        service_namespace: str,
        resource_id: str,
        scalable_dimension: str,
        policy_name: str,
    ) -> str:
        return (
            f"{service_namespace}\t{resource_id}\t{scalable_dimension}\t{policy_name}"
        )


class FakeScheduledAction(BaseModel):
    def __init__(
        self,
        service_namespace: str,
        schedule: str,
        timezone: str,
        scheduled_action_name: str,
        resource_id: str,
        scalable_dimension: str,
        start_time: str,
        end_time: str,
        scalable_target_action: str,
        account_id: str,
        region: str,
    ) -> None:
        self.arn = f"arn:aws:autoscaling:{region}:{account_id}:scheduledAction:{service_namespace}:scheduledActionName/{scheduled_action_name}"
        self.service_namespace = service_namespace
        self.schedule = schedule
        self.timezone = timezone
        self.scheduled_action_name = scheduled_action_name
        self.resource_id = resource_id
        self.scalable_dimension = scalable_dimension
        self.start_time = start_time
        self.end_time = end_time
        self.scalable_target_action = scalable_target_action
        self.creation_time = time.time()

    def update(
        self,
        schedule: str,
        timezone: str,
        scheduled_action_name: str,
        start_time: str,
        end_time: str,
        scalable_target_action: str,
    ) -> None:
        if scheduled_action_name:
            self.scheduled_action_name = scheduled_action_name
        if schedule:
            self.schedule = schedule
        if timezone:
            self.timezone = timezone
        if scalable_target_action:
            self.scalable_target_action = scalable_target_action
        self.start_time = start_time
        self.end_time = end_time


applicationautoscaling_backends = BackendDict(ApplicationAutoscalingBackend, "ec2")
