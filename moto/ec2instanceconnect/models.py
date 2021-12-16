import json
from moto.core import BaseBackend
from moto.core.utils import BackendDict


class Ec2InstanceConnectBackend(BaseBackend):
    def __init__(self, region=None):
        pass

    def send_ssh_public_key(self):
        return json.dumps(
            {"RequestId": "example-2a47-4c91-9700-e37e85162cb6", "Success": True}
        )


ec2instanceconnect_backends = BackendDict(Ec2InstanceConnectBackend, "ec2")
