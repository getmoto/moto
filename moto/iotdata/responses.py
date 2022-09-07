from moto.core.responses import BaseResponse
from .models import iotdata_backends
import json
from urllib.parse import unquote


class IoTDataPlaneResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="iot-data")

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

    def dispatch_publish(self, request, full_url, headers):
        # This endpoint requires specialized handling because it has
        # a uri parameter containing forward slashes that is not
        # correctly url encoded when we're running in server mode.
        # https://github.com/pallets/flask/issues/900
        self.setup_class(request, full_url, headers)
        self.querystring["Action"] = ["Publish"]
        topic = self.path.partition("/topics/")[-1]
        self.querystring["target"] = [unquote(topic)] if "%" in topic else [topic]
        return self.call_action()

    def publish(self):
        topic = self._get_param("target")
        self.iotdata_backend.publish(topic=topic, payload=self.body)
        return json.dumps(dict())
