from moto.core.responses import BaseResponse
from moto.ec2instanceconnect.models import Ec2InstanceConnectBackend


class Ec2InstanceConnectResponse(BaseResponse):
    def send_ssh_public_key(self):
        return ec2_ic_backend.send_ssh_public_key()


ec2_ic_backend = Ec2InstanceConnectBackend()
