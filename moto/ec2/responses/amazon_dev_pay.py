from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class AmazonDevPay(object):
    def confirm_product_instance(self):
        raise NotImplementedError('AmazonDevPay.confirm_product_instance is not yet implemented')
