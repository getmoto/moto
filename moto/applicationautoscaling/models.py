from __future__ import unicode_literals
from moto.core import BaseBackend, BaseModel
from moto.ecs import ecs_backends
from boto3 import Session
from collections import OrderedDict
import time


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
        self.__init__(region, ecs_backend)

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

    def describe_scalable_targets(
        self, namespace, r_ids=None, dimension=None,
    ):
        """ Describe scalable targets. """
        if r_ids is None:
            r_ids = []
        # TODO Validate that if scalable_dimension is supplied then resource_ids must not be empty
        targets = self._flatten_scalable_targets(namespace)
        if dimension is not None:
            targets = [t for t in targets if t.scalable_dimension == dimension]
        if len(r_ids) > 0:
            targets = [t for t in targets if t.resource_id in r_ids]
        return targets

    def _flatten_scalable_targets(self, namespace):
        """ Flatten scalable targets for a given service namespace down to a list. """
        targets = []
        for resource_id in self.targets[namespace].keys():
            for dimension in self.targets[namespace][resource_id].keys():
                targets.append(self.targets[namespace][resource_id][dimension])
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

    def register_scalable_target(self, namespace, r_id, dimension, **kwargs):
        """ Registers or updates a scalable target. """
        # describe_services
        if self._scalable_target_exists(namespace, r_id, dimension):
            target = self.targets[namespace][r_id][dimension]
            target.update(kwargs)
        else:
            target = FakeScalableTarget(self, namespace, r_id, dimension, **kwargs)
            self._add_scalable_target(target)
        return target

    def _scalable_target_exists(self, namespace, r_id, dimension):
        exists = False
        if r_id in self.targets.get(namespace, []) and dimension in self.targets[
            namespace
        ].get(r_id, []):
            exists = True
        return exists

    def _add_scalable_target(self, target):
        if target.service_namespace not in self.targets:
            self.targets[target.service_namespace] = OrderedDict()
        if target.resource_id not in self.targets:
            self.targets[target.service_namespace][target.resource_id] = OrderedDict()
        self.targets[target.service_namespace][target.resource_id][
            target.scalable_dimension
        ] = target
        return target


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
