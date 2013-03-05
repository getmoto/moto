from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VMExport(object):
    def cancel_export_task(self):
        raise NotImplementedError('VMExport.cancel_export_task is not yet implemented')

    def create_instance_export_task(self):
        raise NotImplementedError('VMExport.create_instance_export_task is not yet implemented')

    def describe_export_tasks(self):
        raise NotImplementedError('VMExport.describe_export_tasks is not yet implemented')
