from __future__ import unicode_literals
from moto.core.responses import BaseResponse
import json
from .models import (
    applicationautoscaling_backends,
    ScalableDimensionValueSet,
    ServiceNamespaceValueSet,
)
from .exceptions import AWSValidationException


class ApplicationAutoScalingResponse(BaseResponse):
    @property
    def applicationautoscaling_backend(self):
        return applicationautoscaling_backends[self.region]

    def describe_scalable_targets(self):
        self._validate_params()
        service_namespace = self._get_param("ServiceNamespace")
        resource_ids = self._get_param("ResourceIds")
        scalable_dimension = self._get_param("ScalableDimension")
        max_results = self._get_int_param("MaxResults", 50)
        marker = self._get_param("NextToken")
        all_scalable_targets = self.applicationautoscaling_backend.describe_scalable_targets(
            service_namespace, resource_ids, scalable_dimension
        )
        start = int(marker) + 1 if marker else 0
        next_token = None
        scalable_targets_resp = all_scalable_targets[start : start + max_results]
        if len(all_scalable_targets) > start + max_results:
            next_token = str(len(scalable_targets_resp) - 1)
        targets = [_build_target(t) for t in scalable_targets_resp]
        return json.dumps({"ScalableTargets": targets, "NextToken": next_token})

    def register_scalable_target(self):
        """ Registers or updates a scalable target. """
        self._validate_params()
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

    def deregister_scalable_target(self):
        """ Deregisters a scalable target. """
        self._validate_params()
        self.applicationautoscaling_backend.deregister_scalable_target(
            self._get_param("ServiceNamespace"),
            self._get_param("ResourceId"),
            self._get_param("ScalableDimension"),
        )
        return json.dumps({})

    def put_scaling_policy(self):
        policy = self.applicationautoscaling_backend.put_scaling_policy(
            policy_name=self._get_param("PolicyName"),
            service_namespace=self._get_param("ServiceNamespace"),
            resource_id=self._get_param("ResourceId"),
            scalable_dimension=self._get_param("ScalableDimension"),
            policy_type=self._get_param("PolicyType"),
            policy_body=self._get_param(
                "StepScalingPolicyConfiguration",
                self._get_param("TargetTrackingScalingPolicyConfiguration"),
            ),
        )
        return json.dumps({"PolicyARN": policy.policy_arn, "Alarms": []})  # ToDo

    def describe_scaling_policies(self):
        (
            next_token,
            policy_page,
        ) = self.applicationautoscaling_backend.describe_scaling_policies(
            service_namespace=self._get_param("ServiceNamespace"),
            resource_id=self._get_param("ResourceId"),
            scalable_dimension=self._get_param("ScalableDimension"),
            max_results=self._get_param("MaxResults"),
            next_token=self._get_param("NextToken"),
        )
        response_obj = {"ScalingPolicies": [_build_policy(p) for p in policy_page]}
        if next_token:
            response_obj["NextToken"] = next_token
        return json.dumps(response_obj)

    def delete_scaling_policy(self):
        self.applicationautoscaling_backend.delete_scaling_policy(
            policy_name=self._get_param("PolicyName"),
            service_namespace=self._get_param("ServiceNamespace"),
            resource_id=self._get_param("ResourceId"),
            scalable_dimension=self._get_param("ScalableDimension"),
        )
        return json.dumps({})

    def _validate_params(self):
        """Validate parameters.
        TODO Integrate this validation with the validation in models.py
        """
        namespace = self._get_param("ServiceNamespace")
        dimension = self._get_param("ScalableDimension")
        messages = []
        dimensions = [d.value for d in ScalableDimensionValueSet]
        message = None
        if dimension is not None and dimension not in dimensions:
            messages.append(
                "Value '{}' at 'scalableDimension' "
                "failed to satisfy constraint: Member must satisfy enum value set: "
                "{}".format(dimension, dimensions)
            )
        namespaces = [n.value for n in ServiceNamespaceValueSet]
        if namespace is not None and namespace not in namespaces:
            messages.append(
                "Value '{}' at 'serviceNamespace' "
                "failed to satisfy constraint: Member must satisfy enum value set: "
                "{}".format(namespace, namespaces)
            )
        if len(messages) == 1:
            message = "1 validation error detected: {}".format(messages[0])
        elif len(messages) > 1:
            message = "{} validation errors detected: {}".format(
                len(messages), "; ".join(messages)
            )
        if message:
            raise AWSValidationException(message)


def _build_target(t):
    return {
        "CreationTime": t.creation_time,
        "ServiceNamespace": t.service_namespace,
        "ResourceId": t.resource_id,
        "RoleARN": t.role_arn,
        "ScalableDimension": t.scalable_dimension,
        "MaxCapacity": t.max_capacity,
        "MinCapacity": t.min_capacity,
        "SuspendedState": t.suspended_state,
    }


def _build_policy(p):
    response = {
        "PolicyARN": p.policy_arn,
        "PolicyName": p.policy_name,
        "ServiceNamespace": p.service_namespace,
        "ResourceId": p.resource_id,
        "ScalableDimension": p.scalable_dimension,
        "PolicyType": p.policy_type,
        "CreationTime": p.creation_time,
    }
    if p.policy_type == "StepScaling":
        response["StepScalingPolicyConfiguration"] = p.step_scaling_policy_configuration
    elif p.policy_type == "TargetTrackingScaling":
        response[
            "TargetTrackingScalingPolicyConfiguration"
        ] = p.target_tracking_scaling_policy_configuration
    return response
