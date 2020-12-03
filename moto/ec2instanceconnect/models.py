from boto3 import Session
import json
from moto.core import BaseBackend


class Ec2InstanceConnectBackend(BaseBackend):
    def send_ssh_public_key(self):
        return json.dumps(
            {"RequestId": "example-2a47-4c91-9700-e37e85162cb6", "Success": True}
        )


ec2instanceconnect_backends = {}
for region in Session().get_available_regions("ec2"):
    ec2instanceconnect_backends[region] = Ec2InstanceConnectBackend()
for region in Session().get_available_regions("ec2", partition_name="aws-us-gov"):
    ec2instanceconnect_backends[region] = Ec2InstanceConnectBackend()
for region in Session().get_available_regions("ec2", partition_name="aws-cn"):
    ec2instanceconnect_backends[region] = Ec2InstanceConnectBackend()
