from __future__ import unicode_literals
import time
import boto3
from moto.core import BaseBackend, BaseModel
from collections import OrderedDict
from .exceptions import (
    ResourceNotFoundException,
    InvalidRequestException
)


class FakeThing(BaseModel):
    def __init__(self, thing_name, thing_type, attributes, region_name):
        self.region_name = region_name
        self.thing_name = thing_name
        self.thing_type = thing_type
        self.attributes = attributes
        self.arn = 'arn:aws:iot:%s:1:thing/%s' % (self.region_name, thing_name)
        self.version = 1
        # TODO: we need to handle 'version'?

    def to_json(self, include_default_client_id=False):
        obj = {
            'thingName': self.thing_name,
            'thingTypeName': self.thing_type.thing_type_name,
            'attributes': self.attributes,
            'version': self.version
        }
        if include_default_client_id:
            obj['defaultClientId'] = self.thing_name
        return obj


class FakeThingType(BaseModel):
    def __init__(self, thing_type_name, thing_type_properties, region_name):
        self.region_name = region_name
        self.thing_type_name = thing_type_name
        self.thing_type_properties = thing_type_properties
        t = time.time()
        self.metadata = {
            'deprecated': False,
            'creationData': int(t * 1000) / 1000.0
        }
        self.arn = 'arn:aws:iot:%s:1:thingtype/%s' % (self.region_name, thing_type_name)

    def to_json(self):
        return {
            'thingTypeName': self.thing_type_name,
            'thingTypeProperties': self.thing_type_properties,
            'thingTypeMetadata': self.metadata
        }


class IoTBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(IoTBackend, self).__init__()
        self.region_name = region_name
        self.things = OrderedDict()
        self.thing_types = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_thing(self, thing_name, thing_type_name, attribute_payload):
        thing_types = self.list_thing_types()
        filtered_thing_types = [_ for _ in thing_types if _.thing_type_name == thing_type_name]
        if len(filtered_thing_types) == 0:
            raise ResourceNotFoundException()
        thing_type = filtered_thing_types[0]
        if attribute_payload is None:
            attributes = {}
        elif 'attributes' not in attribute_payload:
            attributes = {}
        else:
            attributes = attribute_payload['attributes']
        thing = FakeThing(thing_name, thing_type, attributes, self.region_name)
        self.things[thing.arn] = thing
        return thing.thing_name, thing.arn

    def create_thing_type(self, thing_type_name, thing_type_properties):
        if thing_type_properties is None:
            thing_type_properties = {}
        thing_type = FakeThingType(thing_type_name, thing_type_properties, self.region_name)
        self.thing_types[thing_type.arn] = thing_type
        return thing_type.thing_type_name, thing_type.arn

    def list_thing_types(self, thing_type_name=None):
        if thing_type_name:
            # It's wierd but thing_type_name is filterd by forward match, not complete match
            return [_ for _ in self.thing_types.values() if _.thing_type_name.startswith(thing_type_name)]
        thing_types = self.thing_types.values()
        return thing_types

    def list_things(self, attribute_name, attribute_value, thing_type_name):
        # TODO: filter by attributess or thing_type
        things = self.things.values()
        return things

    def describe_thing(self, thing_name):
        things = [_ for _ in self.things.values() if _.thing_name == thing_name]
        if len(things) == 0:
            raise ResourceNotFoundException()
        return things[0]

    def describe_thing_type(self, thing_type_name):
        thing_types = [_ for _ in self.thing_types.values() if _.thing_type_name == thing_type_name]
        if len(thing_types) == 0:
            raise ResourceNotFoundException()
        return thing_types[0]

    def delete_thing(self, thing_name, expected_version):
        # TODO: handle expected_version

        # can raise ResourceNotFoundError
        thing = self.describe_thing(thing_name)
        del self.things[thing.arn]

    def delete_thing_type(self, thing_type_name):
        # can raise ResourceNotFoundError
        thing_type = self.describe_thing_type(thing_type_name)
        del self.thing_types[thing_type.arn]

    def update_thing(self, thing_name, thing_type_name, attribute_payload, expected_version, remove_thing_type):
        # if attributes payload = {}, nothing
        thing = self.describe_thing(thing_name)
        thing_type = None

        if remove_thing_type and thing_type_name:
            raise InvalidRequestException()

        # thing_type
        if thing_type_name:
            thing_types = self.list_thing_types()
            filtered_thing_types = [_ for _ in thing_types if _.thing_type_name == thing_type_name]
            if len(filtered_thing_types) == 0:
                raise ResourceNotFoundException()
            thing_type = filtered_thing_types[0]
            thing.thing_type = thing_type

        if remove_thing_type:
            thing.thing_type = None

        # attribute
        if attribute_payload is not None and 'attributes' in attribute_payload:
            do_merge = attribute_payload.get('merge', False)
            attributes = attribute_payload['attributes']
            if not do_merge:
                thing.attributes = attributes
            else:
                thing.attributes.update(attributes)

available_regions = boto3.session.Session().get_available_regions("iot")
iot_backends = {region: IoTBackend(region) for region in available_regions}
