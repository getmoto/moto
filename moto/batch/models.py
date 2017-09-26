from __future__ import unicode_literals
import boto3
from moto.core import BaseBackend, BaseModel


class BatchBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(BatchBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_compute_environment(self, compute_environment_name, type, state, compute_resources, service_role):
        # implement here
        return compute_environment_name, compute_environment_arn
    # add methods from here


available_regions = boto3.session.Session().get_available_regions("batch")
batch_backends = {region: BatchBackend for region in available_regions}
