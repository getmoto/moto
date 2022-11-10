import json
import time
import jsondiff

from moto.core import BaseBackend, BaseModel
from moto.core.utils import merge_dicts, BackendDict
from moto.iot import iot_backends
from .exceptions import (
    ConflictException,
    ResourceNotFoundException,
    InvalidRequestException,
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

        self.metadata_desired = self._create_metadata_from_state(
            self.desired, self.timestamp
        )
        self.metadata_reported = self._create_metadata_from_state(
            self.reported, self.timestamp
        )

    @classmethod
    def create_from_previous_version(cls, previous_shadow, payload):
        """
        set None to payload when you want to delete shadow
        """
        version, previous_payload = (
            (previous_shadow.version + 1, previous_shadow.to_dict(include_delta=False))
            if previous_shadow
            else (1, {})
        )

        if payload is None:
            # if given payload is None, delete existing payload
            # this means the request was delete_thing_shadow
            shadow = FakeShadow(None, None, None, version, deleted=True)
            return shadow

        # Updates affect only the fields specified in the request state document.
        # Any field with a value of None is removed from the device's shadow.
        state_document = previous_payload.copy()
        merge_dicts(state_document, payload, remove_nulls=True)
        desired = state_document.get("state", {}).get("desired")
        reported = state_document.get("state", {}).get("reported")
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
        desired = self.requested_payload["state"].get("desired", None)
        reported = self.requested_payload["state"].get("reported", None)

        payload = {}
        if desired is not None:
            payload["desired"] = desired
        if reported is not None:
            payload["reported"] = reported

        metadata = {}
        if desired is not None:
            metadata["desired"] = self._create_metadata_from_state(
                desired, self.timestamp
            )
        if reported is not None:
            metadata["reported"] = self._create_metadata_from_state(
                reported, self.timestamp
            )
        return {
            "state": payload,
            "metadata": metadata,
            "timestamp": self.timestamp,
            "version": self.version,
        }

    def to_dict(self, include_delta=True):
        """returning nothing except for just top-level keys for now."""
        if self.deleted:
            return {"timestamp": self.timestamp, "version": self.version}
        delta = self.parse_payload(self.desired, self.reported)
        payload = {}
        if self.desired is not None:
            payload["desired"] = self.desired
        if self.reported is not None:
            payload["reported"] = self.reported
        if include_delta and (delta is not None and len(delta.keys()) != 0):
            payload["delta"] = delta

        metadata = {}
        if self.metadata_desired is not None:
            metadata["desired"] = self.metadata_desired
        if self.metadata_reported is not None:
            metadata["reported"] = self.metadata_reported

        return {
            "state": payload,
            "metadata": metadata,
            "timestamp": self.timestamp,
            "version": self.version,
        }


class IoTDataPlaneBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.published_payloads = list()

    @property
    def iot_backend(self):
        return iot_backends[self.account_id][self.region_name]

    def update_thing_shadow(self, thing_name, payload):
        """
        spec of payload:
          - need node `state`
          - state node must be an Object
          - State contains an invalid node: 'foo'
        """
        thing = self.iot_backend.describe_thing(thing_name)

        # validate
        try:
            payload = json.loads(payload)
        except ValueError:
            raise InvalidRequestException("invalid json")
        if "state" not in payload:
            raise InvalidRequestException("need node `state`")
        if not isinstance(payload["state"], dict):
            raise InvalidRequestException("state node must be an Object")
        if any(_ for _ in payload["state"].keys() if _ not in ["desired", "reported"]):
            raise InvalidRequestException("State contains an invalid node")

        if "version" in payload and thing.thing_shadow.version != payload["version"]:
            raise ConflictException("Version conflict")
        new_shadow = FakeShadow.create_from_previous_version(
            thing.thing_shadow, payload
        )
        thing.thing_shadow = new_shadow
        return thing.thing_shadow

    def get_thing_shadow(self, thing_name):
        thing = self.iot_backend.describe_thing(thing_name)

        if thing.thing_shadow is None or thing.thing_shadow.deleted:
            raise ResourceNotFoundException()
        return thing.thing_shadow

    def delete_thing_shadow(self, thing_name):
        thing = self.iot_backend.describe_thing(thing_name)
        if thing.thing_shadow is None:
            raise ResourceNotFoundException()
        payload = None
        new_shadow = FakeShadow.create_from_previous_version(
            thing.thing_shadow, payload
        )
        thing.thing_shadow = new_shadow
        return thing.thing_shadow

    def publish(self, topic, payload):
        self.published_payloads.append((topic, payload))


iotdata_backends = BackendDict(IoTDataPlaneBackend, "iot")
