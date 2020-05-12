import boto.ec2
import json
from moto.core import BaseBackend


class Ec2InstanceConnectBackend(BaseBackend):
    def send_ssh_public_key(self):
        return json.dumps(
            {"RequestId": "example-2a47-4c91-9700-e37e85162cb6", "Success": True}
        )


ec2instanceconnect_backends = {}
for region in boto.ec2.regions():
    ec2instanceconnect_backends[region.name] = Ec2InstanceConnectBackend()
