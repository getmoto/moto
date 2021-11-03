from moto.core.responses import BaseResponse
from .models import ram_backends
import json


class ResourceAccessManagerResponse(BaseResponse):
    SERVICE_NAME = "ram"

    @property
    def ram_backend(self):
        return ram_backends[self.region]

    @property
    def request_params(self):
        try:
            if self.method == "DELETE":
                return None

            return json.loads(self.body)
        except ValueError:
            return {}

    def create_resource_share(self):
        return json.dumps(self.ram_backend.create_resource_share(**self.request_params))

    def get_resource_shares(self):
        return json.dumps(self.ram_backend.get_resource_shares(**self.request_params))

    def update_resource_share(self):
        return json.dumps(self.ram_backend.update_resource_share(**self.request_params))

    def delete_resource_share(self):
        return json.dumps(
            self.ram_backend.delete_resource_share(self._get_param("resourceShareArn"))
        )

    def enable_sharing_with_aws_organization(self):
        return json.dumps(self.ram_backend.enable_sharing_with_aws_organization())
