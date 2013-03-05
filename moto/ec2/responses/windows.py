from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class Windows(object):
    def bundle_instance(self):
        raise NotImplementedError('Windows.bundle_instance is not yet implemented')

    def cancel_bundle_task(self):
        raise NotImplementedError('Windows.cancel_bundle_task is not yet implemented')

    def describe_bundle_tasks(self):
        raise NotImplementedError('Windows.describe_bundle_tasks is not yet implemented')

    def get_password_data(self):
        raise NotImplementedError('Windows.get_password_data is not yet implemented')
