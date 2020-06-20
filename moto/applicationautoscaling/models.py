from __future__ import unicode_literals
from moto.compat import OrderedDict
from moto.core import BaseBackend
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

    def register_scalable_target(self):
        """ Not yet implemented. """
        pass


applicationautoscaling_backends = {}
for region in Session().get_available_regions("autoscaling"):
    applicationautoscaling_backends[region] = ApplicationAutoscalingBackend()
