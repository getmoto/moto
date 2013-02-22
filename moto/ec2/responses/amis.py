from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class AMIs(object):
    def create_image(self):
        raise NotImplementedError('AMIs.create_image is not yet implemented')

    def deregister_image(self):
        raise NotImplementedError('AMIs.deregister_image is not yet implemented')

    def describe_image_attribute(self):
        raise NotImplementedError('AMIs.describe_image_attribute is not yet implemented')

    def describe_images(self):
        raise NotImplementedError('AMIs.describe_images is not yet implemented')

    def modify_image_attribute(self):
        raise NotImplementedError('AMIs.modify_image_attribute is not yet implemented')

    def register_image(self):
        raise NotImplementedError('AMIs.register_image is not yet implemented')

    def reset_image_attribute(self):
        raise NotImplementedError('AMIs.reset_image_attribute is not yet implemented')

