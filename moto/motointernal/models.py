import boto.awslambda

from moto.core import BaseBackend


class MotoBackend(BaseBackend):
    def __init__(self):
        pass


moto_backends = {}
for region in boto.awslambda.regions():
    moto_backends[region.name] = MotoBackend()
