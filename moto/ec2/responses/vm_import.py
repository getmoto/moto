from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class VMImport(object):
    def cancel_conversion_task(self):
        return NotImplemented

    def describe_conversion_tasks(self):
        return NotImplemented

    def import_instance(self):
        return NotImplemented

    def import_volume(self):
        return NotImplemented

