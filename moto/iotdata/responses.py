from moto.core.responses import BaseResponse
from .models import iotdata_backends
import json
from urllib.parse import unquote


class IoTDataPlaneResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="iot-data")

    def _get_action(self) -> str:
        if self.path and self.path.startswith("/topics/"):
            # Special usecase - there is no way identify this action, besides the URL
            return "publish"
        return super()._get_action()

    @property
    def iotdata_backend(self):
        return iotdata_backends[self.current_account][self.region]

    def update_thing_shadow(self):
        thing_name = self._get_param("thingName")
        payload = self.body
        payload = self.iotdata_backend.update_thing_shadow(
            thing_name=thing_name, payload=payload
        )
        return json.dumps(payload.to_response_dict())

    def get_thing_shadow(self):
        thing_name = self._get_param("thingName")
        payload = self.iotdata_backend.get_thing_shadow(thing_name=thing_name)
        return json.dumps(payload.to_dict())

    def delete_thing_shadow(self):
        thing_name = self._get_param("thingName")
        payload = self.iotdata_backend.delete_thing_shadow(thing_name=thing_name)
        return json.dumps(payload.to_dict())

    def publish(self):
        topic = self.path.split("/topics/")[-1]
        # a uri parameter containing forward slashes is not correctly url encoded when we're running in server mode.
        # https://github.com/pallets/flask/issues/900
        topic = unquote(topic) if "%" in topic else topic
        self.iotdata_backend.publish(topic=topic, payload=self.body)
        return json.dumps(dict())
