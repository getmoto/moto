from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class SpotInstances(object):
    def cancel_spot_instance_requests(self):
        raise NotImplementedError('SpotInstances.cancel_spot_instance_requests is not yet implemented')

    def create_spot_datafeed_subscription(self):
        raise NotImplementedError('SpotInstances.create_spot_datafeed_subscription is not yet implemented')

    def delete_spot_datafeed_subscription(self):
        raise NotImplementedError('SpotInstances.delete_spot_datafeed_subscription is not yet implemented')

    def describe_spot_datafeed_subscription(self):
        raise NotImplementedError('SpotInstances.describe_spot_datafeed_subscription is not yet implemented')

    def describe_spot_instance_requests(self):
        raise NotImplementedError('SpotInstances.describe_spot_instance_requests is not yet implemented')

    def describe_spot_price_history(self):
        raise NotImplementedError('SpotInstances.describe_spot_price_history is not yet implemented')

    def request_spot_instances(self):
        raise NotImplementedError('SpotInstances.request_spot_instances is not yet implemented')

