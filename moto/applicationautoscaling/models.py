from __future__ import unicode_literals
from moto.core import BaseBackend, BaseModel
from boto3 import Session


class ApplicationAutoscalingBackend(BaseBackend):
    def __init__(self, region):
        super(ApplicationAutoscalingBackend, self).__init__()
        self.region = region
        self.scalable_targets = {}

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    @property
    def applicationautoscaling_backend(self):
        return applicationautoscaling_backends[self.region_name]

    def delete_scaling_policy(self):
        """ Not yet implemented. """
        pass

    def delete_scheduled_action(self):
        """ Not yet implemented. """
        pass

    def deregister_scalable_target(self):
        """ Not yet implemented. """
        pass

    def describe_scalable_targets(
        self,
        service_namespace,
        resource_ids=None,
        scalable_dimension=None,
        max_results=50,
    ):
        """ Describe scalable targets. """
        if resource_ids is None:
            resource_ids = []
        # TODO Only return max_results
        # TODO Validate that if scalable_dimension is supplied then resource_ids must not be empty
        targets = [
            t
            for t in self.scalable_targets.values()
            if t.service_namespace == service_namespace
        ]
        if len(resource_ids) > 0:
            targets = [t for t in targets if t.resource_id in resource_ids]
        if scalable_dimension is not None:
            targets = [t for t in targets if t.scalable_dimension == scalable_dimension]

        return targets

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
for region_name in Session().get_available_regions("application-autoscaling"):
    applicationautoscaling_backends[region_name] = ApplicationAutoscalingBackend(
        region_name
    )
