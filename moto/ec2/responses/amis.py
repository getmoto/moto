from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class AMIs(object):
    def create_image(self):
        return NotImplemented

    def deregister_image(self):
        return NotImplemented

    def describe_image_attribute(self):
        return NotImplemented

    def describe_images(self):
        return NotImplemented

    def modify_image_attribute(self):
        return NotImplemented

    def register_image(self):
        return NotImplemented

    def reset_image_attribute(self):
        return NotImplemented

