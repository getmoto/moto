from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class Monitoring(object):
    def monitor_instances(self):
        return NotImplemented

    def unmonitor_instances(self):
        return NotImplemented

