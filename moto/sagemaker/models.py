from moto.core import BaseBackend
from moto.ec2 import ec2_backends

class SageMakerBackend(BaseBackend):
    def __init__(self, region_name=None):
        self._models = {}
        self.region_name = region_name

sagemaker_backends = {}
for region, ec2_backend in ec2_backends.items():
    sagemaker_backends[region] = SageMakerBackend()