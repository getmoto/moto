from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class SpotInstances(object):
    def cancel_spot_instance_requests(self):
        return NotImplemented

    def create_spot_datafeed_subscription(self):
        return NotImplemented

    def delete_spot_datafeed_subscription(self):
        return NotImplemented

    def describe_spot_datafeed_subscription(self):
        return NotImplemented

    def describe_spot_instance_requests(self):
        return NotImplemented

    def describe_spot_price_history(self):
        return NotImplemented

    def request_spot_instances(self):
        return NotImplemented

