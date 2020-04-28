import boto.ec2
from moto.core import BaseBackend


class Ec2InstanceConnectBackend(BaseBackend):
    pass


ec2_instance_connect_backends = {}
for region in boto.ec2.regions():
    ec2_instance_connect_backends[region.name] = Ec2InstanceConnectBackend()
