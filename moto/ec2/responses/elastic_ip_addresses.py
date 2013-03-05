from jinja2 import Template

from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class ElasticIPAddresses(object):
    def allocate_address(self):
        raise NotImplementedError('ElasticIPAddresses.allocate_address is not yet implemented')

    def associate_address(self):
        raise NotImplementedError('ElasticIPAddresses.associate_address is not yet implemented')

    def describe_addresses(self):
        raise NotImplementedError('ElasticIPAddresses.describe_addresses is not yet implemented')

    def disassociate_address(self):
        raise NotImplementedError('ElasticIPAddresses.disassociate_address is not yet implemented')

    def release_address(self):
        raise NotImplementedError('ElasticIPAddresses.release_address is not yet implemented')
