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
            service_namespace, resource_ids, scalable_dimension
        )
        start = int(marker) + 1 if marker else 0
        next_token = None
        scalable_targets_resp = all_scalable_targets[start : start + max_results]
        if len(all_scalable_targets) > start + max_results:
            next_token = str(len(scalable_targets_resp) - 1)
        targets = [
            _build_target(t)
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
        try:
            self.applicationautoscaling_backend.register_scalable_target(
                self._get_param("ServiceNamespace"),
                self._get_param("ResourceId"),
                self._get_param("ScalableDimension"),
                min_capacity=self._get_int_param("MinCapacity"),
                max_capacity=self._get_int_param("MaxCapacity"),
                role_arn=self._get_param("RoleARN"),
                suspended_state=self._get_param("SuspendedState"),
            )
        except AWSValidationException as e:
            return e.response()
        return json.dumps({})

    def _validate_params(self):
        namespace = self._get_param("ServiceNamespace")
        dimension = self._get_param("ScalableDimension")
        messages = []
        resp = None
        dimensions = [d.value for d in ScalableDimensionValueSet]
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
            resp = AWSValidationException(
                "1 validation error detected: {}".format(messages[0])
            ).response()
        elif len(messages) > 1:
            resp = AWSValidationException(
                "{} validation errors detected: {}".format(
                    len(messages), "; ".join(messages)
                )
            ).response()
        return resp


def _build_target(t):
    return {
        "CreationTime": t.creation_time,
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
