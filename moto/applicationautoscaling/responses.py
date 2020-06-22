from __future__ import unicode_literals
from moto.core.responses import BaseResponse
import json
from .models import applicationautoscaling_backends


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
        service_namespace = self._get_param("ServiceNamespace")
        resource_ids = self._get_multi_param("ResourceIds")
        scalable_dimension = self._get_param("ScalableDimension")
        max_results = self._get_int_param("MaxResults", 50)
        all_scalable_targets = self.applicationautoscaling_backend.describe_scalable_targets(
            service_namespace, resource_ids, scalable_dimension
        )
        marker = self._get_param("NextToken")
        start = all_scalable_targets.index(marker) + 1 if marker else 0
        next_token = None
        scalable_targets_resp = all_scalable_targets[start: start + max_results]
        if len(all_scalable_targets) > start + max_results:
            next_token = scalable_targets_resp[-1].name
        targets = [{
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
        } for t in scalable_targets_resp]
        return json.dumps({
            "ScalableTargets": targets,
            "NextToken": next_token
        })

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
        self.applicationautoscaling_backend.register_scalable_target(
            service_namespace=self._get_param("ServiceNamespace"),
            resource_id=self._get_param("ResourceId"),
            scalable_dimension=self._get_param("ScalableDimension"),
            min_capacity=self._get_int_param("MinCapacity"),
            max_capacity=self._get_int_param("MaxCapacity"),
            role_arn=self._get_param("RoleARN"),
            suspended_state=self._get_param("SuspendedState")
        )
        return json.dumps({})
