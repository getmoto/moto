from __future__ import unicode_literals
import json
import time
import boto3
import jsondiff
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
    def __init__(self, desired, reported, requested_payload, version, deleted=False):
        self.desired = desired
        self.reported = reported
        self.requested_payload = requested_payload
        self.version = version
        self.timestamp = int(time.time())
        self.deleted = deleted

        self.metadata_desired = self._create_metadata_from_state(self.desired, self.timestamp)
        self.metadata_reported = self._create_metadata_from_state(self.reported, self.timestamp)

    @classmethod
    def create_from_previous_version(cls, previous_shadow, payload):
        """
        set None to payload when you want to delete shadow
        """
        version, previous_payload = (previous_shadow.version + 1, previous_shadow.to_dict(include_delta=False)) if previous_shadow else (1, {})

        if payload is None:
            # if given payload is None, delete existing payload
            # this means the request was delete_thing_shadow
            shadow = FakeShadow(None, None, None, version, deleted=True)
            return shadow

        # we can make sure that payload has 'state' key
        desired = payload['state'].get(
            'desired',
            previous_payload.get('state', {}).get('desired', None)
        )
        reported = payload['state'].get(
            'reported',
            previous_payload.get('state', {}).get('reported', None)
        )
        shadow = FakeShadow(desired, reported, payload, version)
        return shadow

    @classmethod
    def parse_payload(cls, desired, reported):
        if desired is None:
            delta = reported
        elif reported is None:
            delta = desired
        else:
            delta = jsondiff.diff(desired, reported)
        return delta

    def _create_metadata_from_state(self, state, ts):
        """
        state must be disired or reported stype dict object
        replces primitive type with {"timestamp": ts} in dict
        """
        if state is None:
            return None

        def _f(elem, ts):
            if isinstance(elem, dict):
                return {_: _f(elem[_], ts) for _ in elem.keys()}
            if isinstance(elem, list):
                return [_f(_, ts) for _ in elem]
            return {"timestamp": ts}
        return _f(state, ts)

    def to_response_dict(self):
        desired = self.requested_payload['state'].get('desired', None)
        reported = self.requested_payload['state'].get('reported', None)

        payload = {}
        if desired is not None:
            payload['desired'] = desired
        if reported is not None:
            payload['reported'] = reported

        metadata = {}
        if desired is not None:
            metadata['desired'] = self._create_metadata_from_state(desired, self.timestamp)
        if reported is not None:
            metadata['reported'] = self._create_metadata_from_state(reported, self.timestamp)
        return {
            'state': payload,
            'metadata': metadata,
            'timestamp': self.timestamp,
            'version': self.version
        }

    def to_dict(self, include_delta=True):
        """returning nothing except for just top-level keys for now.
        """
        if self.deleted:
            return {
                'timestamp': self.timestamp,
                'version': self.version
            }
        delta = self.parse_payload(self.desired, self.reported)
        payload = {}
        if self.desired is not None:
            payload['desired'] = self.desired
        if self.reported is not None:
            payload['reported'] = self.reported
        if include_delta and (delta is not None and len(delta.keys()) != 0):
            payload['delta'] = delta

        metadata = {}
        if self.metadata_desired is not None:
            metadata['desired'] = self.metadata_desired
        if self.metadata_reported is not None:
            metadata['reported'] = self.metadata_reported

        return {
            'state': payload,
            'metadata': metadata,
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
            payload = json.loads(payload)
        except ValueError:
            raise InvalidRequestException('invalid json')
        if 'state' not in payload:
            raise InvalidRequestException('need node `state`')
        if not isinstance(payload['state'], dict):
            raise InvalidRequestException('state node must be an Object')
        if any(_ for _ in payload['state'].keys() if _ not in ['desired', 'reported']):
            raise InvalidRequestException('State contains an invalid node')

        new_shadow = FakeShadow.create_from_previous_version(thing.thing_shadow, payload)
        thing.thing_shadow = new_shadow
        return thing.thing_shadow

    def get_thing_shadow(self, thing_name):
        thing = iot_backends[self.region_name].describe_thing(thing_name)

        if thing.thing_shadow is None or thing.thing_shadow.deleted:
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
        # do nothing because client won't know about the result
        return None


available_regions = boto3.session.Session().get_available_regions("iot-data")
iotdata_backends = {region: IoTDataPlaneBackend(region) for region in available_regions}
