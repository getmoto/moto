from __future__ import unicode_literals
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from boto3 import Session


class ApplicationAutoscalingBackend(BaseBackend):

    def __init__(self):
        self.scalable_targets = OrderedDict()

    def delete_scaling_policy(self):
        """ Not yet implemented. """
        pass

    def delete_scheduled_action(self):
        """ Not yet implemented. """
        pass

    def deregister_scalable_target(self):
        """ Not yet implemented. """
        pass

    def describe_scalable_targets(self, service_namespace, resource_ids, scalable_dimension):
        """ Describe scalable targets. """
        # TODO Filter by service_namespace
        # TODO Only return selected resource_ids
        # TODO Filter by scalable_dimension
        return list(self.scalable_targets.values())

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

    def register_scalable_target(self, **kwargs):
        """ Registers or updates a scalable target. """
        resource_id = kwargs["resource_id"]
        if resource_id in self.scalable_targets:
            target = self.scalable_targets[resource_id]
            target.update(kwargs)
        else:
            target = FakeScalableTarget(self, **kwargs)
            self.scalable_targets[resource_id] = target
        return target


class FakeScalableTarget(BaseModel):

    def __init__(self, backend, **kwargs):
        self.applicationautoscaling_backend = backend
        self.service_namespace = kwargs["service_namespace"]
        self.resource_id = kwargs["resource_id"]
        self.scalable_dimension = kwargs["scalable_dimension"]
        self.min_capacity = kwargs["min_capacity"]
        self.max_capacity = kwargs["max_capacity"]
        self.role_arn = kwargs["role_arn"]
        self.suspended_state = kwargs["suspended_state"]

    def update(self, **kwargs):
        if kwargs["min_capacity"] is not None:
            self.min_capacity = kwargs["min_capacity"]
        if kwargs["max_capacity"] is not None:
            self.max_capacity = kwargs["max_capacity"]


applicationautoscaling_backends = {}
for region in Session().get_available_regions("application-autoscaling"):
    applicationautoscaling_backends[region] = ApplicationAutoscalingBackend()
