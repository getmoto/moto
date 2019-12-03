from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import iotdata_backends
import json


class IoTDataPlaneResponse(BaseResponse):
    SERVICE_NAME = "iot-data"

    @property
    def iotdata_backend(self):
        return iotdata_backends[self.region]

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
        topic = self._get_param("topic")
        qos = self._get_int_param("qos")
        payload = self._get_param("payload")
        self.iotdata_backend.publish(topic=topic, qos=qos, payload=payload)
        return json.dumps(dict())
