from __future__ import unicode_literals

import json
import re

import boto3
import six
from botocore.serialize import Serializer
from pkg_resources import resource_filename

metadata = json.load(
    open(resource_filename(__name__, 'resources/metadata.json'), 'r')
)

VALID_DB_ENGINES = [e for e in metadata['db_engines']]
VALID_DB_CLUSTER_ENGINES = [e for e in metadata['db_engines'] if e.startswith('aurora')]
VALID_DB_INSTANCE_ENGINES = [e for e in metadata['db_engines']]

db_engine_data = metadata['db_engine_data']
db_engine_defaults = metadata['db_engine_defaults']
default_db_cluster_parameter_groups = metadata['default_db_cluster_parameter_groups']
default_db_parameter_groups = metadata['default_db_parameter_groups']
default_option_groups = metadata['default_option_groups']
option_group_options = metadata['option_group_options']


def camelcase_to_underscores(value):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', value)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def parse_cf_properties(operation, properties):
    client = boto3.client('rds', region_name='us-east-1')
    operation_model = client.meta.service_model.operation_model(operation)
    deserializer = CloudFormationPropertiesParser()
    deserialized = deserializer.parse(properties, operation_model.input_shape)
    return deserialized


def parse_query_parameters(operation, query_parameters):
    client = boto3.client('rds', region_name='us-east-1')
    operation_model = client.meta.service_model.operation_model(operation)
    parser = QueryStringParametersParser()
    parsed = parser.parse(query_parameters, operation_model.input_shape)
    return parsed


def valid_engine_versions(engine_name):
    return [engine['EngineVersion'] for engine in db_engine_data
            if engine['Engine'] == engine_name]


def valid_major_engine_versions(engine_name):
    # FIXME: This doesn't work for anything other than version like 9.6.1 or 5.7.2
    return set([engine['EngineVersion'][:3] for engine in db_engine_data
                if engine['Engine'] == engine_name])


def default_engine_version(engine_name):
    defaults = get_engine_defaults(engine_name)
    return defaults['EngineVersion']


def default_engine_port(engine_name):
    # TODO: Move this to metadata
    # Have this be a lookup table and in metadata actually have all the engines listed...
    # We could add 'Port' to the Engine defaults metadata.
    default_engine_ports = {
        'aurora': 3306,
        'aurora-postgresql': 5432,
        'mariadb': 3306,
        'mysql': 3306,
        'oracle': 1521,
        'postgres': 5432,
        'sqlserver': 1433,
    }
    default_port = default_engine_ports.get(engine_name)
    if default_port is None:
        for engine in default_engine_ports:
            if engine_name.startswith(engine):
                default_port = default_engine_ports[engine]
    return default_port or '123'


def default_option_group_name(engine_name, engine_version):
    try:
        option_group = next(og for og in default_option_groups
                            if og['EngineName'] == engine_name and
                            og['MajorEngineVersion'] == engine_version[:len(og['MajorEngineVersion'])])
    except StopIteration:
        option_group = {'OptionGroupName': 'default:{}-{}'.format(engine_name, engine_version.replace('.', '-'))}
    return option_group['OptionGroupName']


def default_db_cluster_parameter_group_name(engine_name):
    defaults = get_engine_defaults(engine_name)
    param_group_family = defaults['DBParameterGroupFamily']
    param_group = next(item for item in default_db_cluster_parameter_groups
                       if item['DBParameterGroupFamily'] == param_group_family)
    return param_group['DBClusterParameterGroupName']


def default_db_parameter_group_name(engine_name, engine_version):
    parameter_group_name = None
    for i in range(len(engine_version), 1, -1):
        try:
            param_group = next(
                item for item in default_db_parameter_groups if
                str(item['DBParameterGroupFamily']).startswith(engine_name) and
                str(item['DBParameterGroupFamily']).endswith(engine_version[0:i])
            )
            parameter_group_name = param_group['DBParameterGroupName']
        except StopIteration:
            pass
    return parameter_group_name or 'default.{}'.format(engine_version)


def get_engine_defaults(engine_name):
    defaults = next(item for item in db_engine_defaults if item['Engine'] == engine_name)
    return defaults


def add_backend_methods(backend):
    def decorate(cls):
        def handle_action(self):
            return self.handle_action()

        for method_name in backend.methods_implemented():
            setattr(cls, method_name, handle_action)
        return cls

    return decorate


# noinspection PyUnusedLocal
class CloudFormationPropertiesParser(object):
    # This deserializes from a dict of properties, but
    # scalar value like 'db_subnet_group_name' might actually
    # be the backend db_subnet_group_entity, so we have to
    # pull from there if needed.

    # Not all CF properties map directly to API parameters...
    SHAPE_NAME_TO_CF_PROPERTY_MAP = {
        'DBParameterGroupFamily': 'Family',
        'DBSecurityGroupDescription': 'GroupDescription',
        'VpcSecurityGroupIds': 'VPCSecurityGroups',
    }

    def __init__(self, convert_to_snake_case=True):
        self.convert_to_snake_case = convert_to_snake_case

    def parse(self, properties, shape):
        parsed = {}
        if shape is not None:
            parsed = self._parse_shape(shape, properties)
        return parsed

    def _parse_shape(self, shape, prop):
        handler = getattr(self, '_handle_%s' % shape.type_name, self._default_handle)
        return handler(shape, prop)

    def _handle_structure(self, shape, prop):
        parsed = {}
        members = shape.members
        for member_name in members:
            member_shape = members[member_name]
            prop_name = self._prop_key_name(member_name)
            prop_value = prop.get(prop_name)
            if prop_value is not None:
                parsed_key = self._parsed_key_name(member_name)
                parsed[parsed_key] = self._parse_shape(member_shape, prop_value)
        return parsed

    def _handle_list(self, shape, prop):
        parsed = []
        member_shape = shape.member
        for item in prop:
            parsed.append(self._parse_shape(member_shape, item))
        return parsed

    @staticmethod
    def _handle_boolean(shape, text):
        if text == 'true':
            return True
        else:
            return False

    @staticmethod
    def _handle_integer(shape, text):
        return int(text)

    @staticmethod
    def _default_handle(shape, value):
        # If value is non-scalar, try to get the scalar from the object.
        if value and not isinstance(value, six.string_types):
            value = getattr(value, 'resource_id', value)
        return value

    def _prop_key_name(self, member_name):
        return self.SHAPE_NAME_TO_CF_PROPERTY_MAP.get(member_name, member_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        if self.convert_to_snake_case:
            key_name = camelcase_to_underscores(key_name)
        return key_name


class QueryStringParametersParser(object):

    def __init__(self, convert_to_snake_case=True):
        self.convert_to_snake_case = convert_to_snake_case

    def parse(self, query_params, shape):
        parsed = {}
        if shape is not None:
            parsed = self._parse_shape(shape, query_params)
        return parsed

    def _parse_shape(self, shape, query_params, prefix=''):
        handler = getattr(self, '_handle_%s' % shape.type_name, self._default_handle)
        return handler(shape, query_params, prefix=prefix)

    def _handle_structure(self, shape, query_params, prefix=''):
        parsed = {}
        members = shape.members
        for member_name in members:
            member_shape = members[member_name]
            member_prefix = self._get_serialized_name(member_shape, member_name)
            if prefix:
                member_prefix = '%s.%s' % (prefix, member_prefix)
            if self._has_member(query_params, member_prefix):
                parsed_key = self._parsed_key_name(member_name)
                parsed[parsed_key] = self._parse_shape(member_shape, query_params, member_prefix)
        return parsed

    def _handle_list(self, shape, query_params, prefix=''):
        parsed = []
        member_shape = shape.member

        list_prefixes = []
        list_names = list({shape.member.serialization.get('name', 'member'), 'member'})
        for list_name in list_names:
            list_prefixes.append('%s.%s' % (prefix, list_name))

        for list_prefix in list_prefixes:
            i = 1
            while self._has_member(query_params, '%s.%s' % (list_prefix, i)):
                parsed.append(
                    self._parse_shape(member_shape, query_params, '%s.%s' % (list_prefix, i)))
                i += 1
        return parsed

    def _handle_boolean(self, shape, query_params, prefix=''):
        value = self._default_handle(shape, query_params, prefix)
        if value.lower() == 'true':
            return True
        else:
            return False

    def _handle_integer(self, shape, query_params, prefix=''):
        value = self._default_handle(shape, query_params, prefix)
        return int(value)

    def _default_handle(self, shape, query_params, prefix=''):
        # urlparse parses all querystring values into lists.
        return query_params.get(prefix)[0]

    def _get_serialized_name(self, shape, default_name):
        return shape.serialization.get('name', default_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        if self.convert_to_snake_case:
            key_name = camelcase_to_underscores(key_name)
        return key_name

    def _has_member(self, value, member_prefix):
        return any(i for i in value if i.startswith(member_prefix))


class DictSerializer(Serializer):

    TIMESTAMP_FORMAT = 'iso8601'

    def serialize_object(self, value, operation_model):

        serialized = {}

        output_shape = operation_model.output_shape
        key = None
        if output_shape is not None:
            start = serialized
            if 'resultWrapper' in output_shape.serialization:
                serialized[output_shape.serialization['resultWrapper']] = {}
                start = serialized[output_shape.serialization['resultWrapper']]
                # key, output_shape = self._find_result_wrapped_shape(
                # output_shape,
                #         value)

                # if hasattr(output_shape, 'member'):
                #     start[key] = {}
                #     start = start[key]
                # key = output_shape.member.name

            self._serialize(start, value, output_shape, key)

        return serialized

    def _find_result_wrapped_shape(self, shape, value):
        for member_key, member_shape in shape.members.items():
            if member_shape.type_name == 'list' and isinstance(value, list):
                if member_shape.member.name == value[0].__class__.__name__:
                    return member_key, member_shape
            if member_key == value.__class__.__name__:
                return member_key, member_shape
        return shape.name, shape

    def _serialize(self, serialized, value, shape, key=None):
        method = getattr(self, '_serialize_type_%s' % shape.type_name, self._default_serialize)
        method(serialized, value, shape, key)

    def _get_value(self, value, key, shape):
        key = camelcase_to_underscores(key)
        if isinstance(value, dict):
            new_value = value.get(key, None)
        elif isinstance(value, object):
            new_value = getattr(value, key, None)
        else:
            new_value = None
        # if new_value is None:
        #     if shape.type_name == 'list':
        #         new_value = []
        #     elif shape.type_name == 'structure':
        #         new_value = {}
        return new_value

    def _serialize_type_structure(self, serialized, value, shape, key):
        if value is None:
            return
        if key is not None:
            # If a key is provided, this is a result of a recursive
            # call so we need to add a new child dict as the value
            # of the passed in serialized dict.  We'll then add
            # all the structure members as key/vals in the new serialized
            # dictionary we just created.
            new_serialized = self.MAP_TYPE()
            serialized[key] = new_serialized
            serialized = new_serialized
        for member_key, member_shape in shape.members.items():
            if 'name' in member_shape.serialization:
                member_key = member_shape.serialization['name']
            member_value = self._get_value(value, member_key, member_shape)
            if member_value is not None:
                self._serialize(serialized, member_value, member_shape, member_key)

    def _serialize_type_map(self, serialized, value, shape, key):
        map_obj = self.MAP_TYPE()
        serialized[key] = map_obj
        for sub_key, sub_value in value.items():
            self._serialize(map_obj, sub_value, shape.value, sub_key)

    def _serialize_type_list(self, serialized, value, shape, key):
        list_obj = []
        serialized[key] = {}
        serialized[key][self._get_serialized_name(shape.member, '')] = list_obj
        for list_item in value:
            wrapper = {}
            # The JSON list serialization is the only case where we aren't
            # setting a key on a dict.  We handle this by using
            # a __current__ key on a wrapper dict to serialize each
            # list item before appending it to the serialized list.
            self._serialize(wrapper, list_item, shape.member, "__current__")
            list_obj.append(wrapper["__current__"])

    def _default_serialize(self, serialized, value, shape, key):
        serialized[key] = value

    def _serialize_type_boolean(self, serialized, value, shape, key):
        serialized[key] = str(value).lower()

    def _serialize_type_timestamp(self, serialized, value, shape, key):
        serialized[key] = self._convert_timestamp_to_str(value)

    def _serialize_type_blob(self, serialized, value, shape, key):
        serialized[key] = self._get_base64(value)

    def _get_serialized_name(self, shape, default_name):
        # Returns the serialized name for the shape if it exists.
        # Otherwise it will return the passed in default_name.
        return shape.serialization.get('name', default_name)

    def serialize_to_request(self, parameters, operation_model):
        # We don't use this, but override it because it's an
        # abstract method on the base class.
        pass