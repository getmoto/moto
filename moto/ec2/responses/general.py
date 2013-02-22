from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class General(object):
    def get_console_output(self):
        return NotImplemented

