from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class Windows(object):
    def bundle_instance(self):
        return NotImplemented

    def cancel_bundle_task(self):
        return NotImplemented

    def describe_bundle_tasks(self):
        return NotImplemented

    def get_password_data(self):
        return NotImplemented

