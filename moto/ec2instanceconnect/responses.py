from moto.core.responses import BaseResponse
from .models import ec2instanceconnect_backends


class Ec2InstanceConnectResponse(BaseResponse):
    @property
    def ec2instanceconnect_backend(self):
        return ec2instanceconnect_backends[self.region]

    def send_ssh_public_key(self):
        return self.ec2instanceconnect_backend.send_ssh_public_key()
