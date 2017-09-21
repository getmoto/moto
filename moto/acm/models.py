from __future__ import unicode_literals

from moto.core import BaseBackend, BaseModel
from moto.ec2 import ec2_backends


class Certificate(BaseModel):
    pass


class AWSCertificateManagerBackend(BaseBackend):

    def __init__(self):
        self._certificates = {}


acm_backends = {}
for region, ec2_backend in ec2_backends.items():
    acm_backends[region] = AWSCertificateManagerBackend()
