from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VMExport(object):
    def cancel_export_task(self):
        return NotImplemented

    def create_instance_export_task(self):
        return NotImplemented

    def describe_export_tasks(self):
        return NotImplemented

