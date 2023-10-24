import json
import urllib

from moto.core.responses import BaseResponse
from .models import panorama_backends, PanoramaBackend


class PanoramaResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="panorama")

    @property
    def panorama_backend(self) -> PanoramaBackend:
        return panorama_backends[self.current_account][self.region]

    def provision_device(self) -> str:
        description = self._get_param("Description")
        name = self._get_param("Name")
        networking_configuration = self._get_param("NetworkingConfiguration")
        tags = self._get_param("Tags")
        device = self.panorama_backend.provision_device(
            description=description,
            name=name,
            networking_configuration=networking_configuration,
            tags=tags,
        )
        return json.dumps(device.response_provision)

    def describe_device(self) -> str:
        device_id = urllib.parse.unquote(self._get_param("DeviceId"))
        device = self.panorama_backend.describe_device(device_id=device_id)
        return json.dumps(device.response_object())
