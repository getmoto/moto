import six
from botocore import xform_name


# noinspection PyUnusedLocal
class CloudFormationPropertiesParser(object):
    # This deserializes from a dict of properties, but
    # scalar value like 'db_subnet_group_name' might actually
    # be the backend db_subnet_group_entity, so we have to
    # pull from there if needed.

    # Not all CF properties map directly to API parameters...
    SHAPE_NAME_TO_CF_PROPERTY_MAP = {
        "DBParameterGroupFamily": "Family",
        "DBSecurityGroupDescription": "GroupDescription",
        "VpcSecurityGroupIds": "VPCSecurityGroups",
    }

    def __init__(self, convert_to_snake_case=True):
        self.convert_to_snake_case = convert_to_snake_case

    def parse(self, properties, shape):
        parsed = {}
        if shape is not None:
            parsed = self._parse_shape(shape, properties)
        return parsed

    def _parse_shape(self, shape, prop):
        handler = getattr(self, "_handle_%s" % shape.type_name, self._default_handle)
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
        if text == "true":
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
            value = getattr(value, "resource_id", value)
        return value

    def _prop_key_name(self, member_name):
        return self.SHAPE_NAME_TO_CF_PROPERTY_MAP.get(member_name, member_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        if self.convert_to_snake_case:
            key_name = xform_name(key_name)
        return key_name


class QueryStringParametersParser(object):
    def __init__(self, convert_to_snake_case=True):
        self.convert_to_snake_case = convert_to_snake_case

    def parse(self, query_params, shape):
        parsed = {}
        if shape is not None:
            parsed = self._parse_shape(shape, query_params)
        return parsed

    def _parse_shape(self, shape, query_params, prefix=""):
        handler = getattr(self, "_handle_%s" % shape.type_name, self._default_handle)
        return handler(shape, query_params, prefix=prefix)

    def _handle_structure(self, shape, query_params, prefix=""):
        parsed = {}
        members = shape.members
        for member_name in members:
            member_shape = members[member_name]
            member_prefix = self._get_serialized_name(member_shape, member_name)
            if prefix:
                member_prefix = "%s.%s" % (prefix, member_prefix)
            if self._has_member(query_params, member_prefix):
                parsed_key = self._parsed_key_name(member_name)
                parsed[parsed_key] = self._parse_shape(
                    member_shape, query_params, member_prefix
                )
        return parsed

    def _handle_list(self, shape, query_params, prefix=""):
        parsed = []
        member_shape = shape.member

        list_prefixes = []
        list_names = list({shape.member.serialization.get("name", "member"), "member"})
        for list_name in list_names:
            list_prefixes.append("%s.%s" % (prefix, list_name))

        for list_prefix in list_prefixes:
            i = 1
            while self._has_member(query_params, "%s.%s" % (list_prefix, i)):
                parsed.append(
                    self._parse_shape(
                        member_shape, query_params, "%s.%s" % (list_prefix, i)
                    )
                )
                i += 1
        return parsed

    def _handle_boolean(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        if value.lower() == "true":
            return True
        else:
            return False

    def _handle_integer(self, shape, query_params, prefix=""):
        value = self._default_handle(shape, query_params, prefix)
        return int(value)

    def _default_handle(self, shape, query_params, prefix=""):
        # urlparse parses all querystring values into lists.
        return query_params.get(prefix)[0]

    def _get_serialized_name(self, shape, default_name):
        return shape.serialization.get("name", default_name)

    def _parsed_key_name(self, member_name):
        key_name = member_name
        if self.convert_to_snake_case:
            key_name = xform_name(key_name)
        return key_name

    def _has_member(self, value, member_prefix):
        return any(i for i in value if i.startswith(member_prefix))
