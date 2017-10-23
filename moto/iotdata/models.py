from __future__ import unicode_literals
import json
import time
import boto3
from moto.core import BaseBackend, BaseModel
from moto.iot import iot_backends
from .exceptions import (
    ResourceNotFoundException,
    InvalidRequestException
)

class FakeShadow(BaseModel):
    """See the specification:
    http://docs.aws.amazon.com/iot/latest/developerguide/thing-shadow-document-syntax.html
    """
    def __init__(self, payload, version, metadata):
        self.payload = payload
        self.version = version
        self.metadata = metadata
        self.timestamp = int(time.time())

    @classmethod
    def create_from_previous_version(cls, previous_shadow, payload):
        # TODO: need to generate metadata
        # TODO: need to generate state of desired/reported/delta

        metadata = {}
        if previous_shadow is None:
            shadow = FakeShadow(payload, 1, metadata)
        else:
            version = previous_shadow.version + 1
            # handle delta/etc..
            shadow = FakeShadow(payload, version, metadata)
        return shadow

    def to_dict(self):
        """returning nothing except for just top-level keys for now.
        """
        if self.payload is None:
            return {
                'timestamp': self.timestamp,
                'version': self.version
            }
        return {
            'state': {},
            'metadata': {},
            'timestamp': self.timestamp,
            'version': self.version
        }


class IoTDataPlaneBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(IoTDataPlaneBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def update_thing_shadow(self, thing_name, payload):
        """
        spec of payload:
          - need node `state`
          - state node must be an Object
          - State contains an invalid node: 'foo'
        """
        thing = iot_backends[self.region_name].describe_thing(thing_name)

        # validate
        try:
            j = json.loads(payload)
        except:
            raise InvalidRequestException('invalid json')
        if 'state' not in j:
            raise InvalidRequestException('need node `state`')
        if not isinstance(j['state'], dict):
            raise InvalidRequestException('state node must be an Object')
        if any(_ for _ in j['state'].keys() if _ not in ['desired', 'reported']):
            raise InvalidRequestException('State contains an invalid node')

        new_shadow = FakeShadow.create_from_previous_version(thing.thing_shadow, payload)
        thing.thing_shadow = new_shadow
        return thing.thing_shadow

    def get_thing_shadow(self, thing_name):
        thing = iot_backends[self.region_name].describe_thing(thing_name)

        if thing.thing_shadow is None or thing.thing_shadow.payload is None:
            raise ResourceNotFoundException()
        return thing.thing_shadow

    def delete_thing_shadow(self, thing_name):
        """after deleting, get_thing_shadow will raise ResourceNotFound.
        But version of the shadow keep increasing...
        """
        thing = iot_backends[self.region_name].describe_thing(thing_name)
        if thing.thing_shadow is None:
            raise ResourceNotFoundException()
        payload = None
        new_shadow = FakeShadow.create_from_previous_version(thing.thing_shadow, payload)
        thing.thing_shadow = new_shadow
        return thing.thing_shadow

    def publish(self, topic, qos, payload):
        # Do nothing for now.
        return

available_regions = boto3.session.Session().get_available_regions("iot-data")
iotdata_backends = {region: IoTDataPlaneBackend(region) for region in available_regions}
