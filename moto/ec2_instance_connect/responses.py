import json
from moto.core.responses import BaseResponse


class Ec2InstanceConnectResponse(BaseResponse):
    def send_ssh_public_key(self):
        return json.dumps(
            {"RequestId": "example-2a47-4c91-9700-e37e85162cb6", "Success": True}
        )
