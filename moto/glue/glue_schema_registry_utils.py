import re
import json

from .glue_schema_registry_constants import (
    MAX_REGISTRY_NAME_LENGTH,
    RESOURCE_NAME_PATTERN,
    MAX_ARN_LENGTH,
    ARN_PATTERN,
    MAX_DESCRIPTION_LENGTH,
    DESCRIPTION_PATTERN,
    MAX_SCHEMA_NAME_LENGTH,
    DEFAULT_REGISTRY_NAME,
    REGISTRY_NAME,
    REGISTRY_ARN,
    SCHEMA_NAME,
    SCHEMA_ARN,
    MAX_TAGS_ALLOWED,
    MAX_SCHEMA_DEFINITION_LENGTH,
    SCHEMA_DEFINITION,
    MAX_SCHEMAS_ALLOWED,
    MAX_SCHEMA_VERSIONS_ALLOWED,
    MAX_REGISTRIES_ALLOWED,
)

from .exceptions import (
    ResourceNameTooLongException,
    ParamValueContainsInvalidCharactersException,
    InvalidSchemaDefinitionException,
    InvalidRegistryIdBothParamsProvidedException,
    GSREntityNotFoundException,
    InvalidSchemaIdBothParamsProvidedException,
    InvalidSchemaIdInsufficientParamsProvidedException,
    SchemaNotFoundException,
    InvalidDataFormatException,
    InvalidCompatibilityException,
    InvalidNumberOfTagsException,
    GSRAlreadyExistsException,
    ResourceNumberLimitExceededException,
    DisabledCompatibilityVersioningException,
)


def validate_registry_name_pattern_and_length(param_value):
    param_name = "registryName"
    max_name_length = MAX_REGISTRY_NAME_LENGTH
    pattern = RESOURCE_NAME_PATTERN
    validate_param_pattern_and_length(param_value, param_name, max_name_length, pattern)


def validate_arn_pattern_and_length(param_value):
    param_name = "registryArn"
    max_name_length = MAX_ARN_LENGTH
    pattern = ARN_PATTERN
    validate_param_pattern_and_length(param_value, param_name, max_name_length, pattern)


def validate_description_pattern_and_length(param_value):
    param_name = "description"
    max_name_length = MAX_DESCRIPTION_LENGTH
    pattern = DESCRIPTION_PATTERN
    validate_param_pattern_and_length(param_value, param_name, max_name_length, pattern)


def validate_schema_name_pattern_and_length(param_value):
    param_name = "schemaName"
    max_name_length = MAX_SCHEMA_NAME_LENGTH
    pattern = RESOURCE_NAME_PATTERN
    validate_param_pattern_and_length(param_value, param_name, max_name_length, pattern)


def validate_param_pattern_and_length(
    param_value, param_name, max_name_length, pattern
):
    if len(param_value.encode("utf-8")) > max_name_length:
        raise ResourceNameTooLongException(param_name)

    if re.match(pattern, param_value) is None:
        raise ParamValueContainsInvalidCharactersException(param_name)


def validate_number_of_tags(tags):
    if len(tags) > MAX_TAGS_ALLOWED:
        raise InvalidNumberOfTagsException()


def validate_avro_json_schema_definition(data_format, schema_definition):
    if data_format in ["AVRO", "JSON"]:
        try:
            json.loads(schema_definition)
        except ValueError as err:
            raise InvalidSchemaDefinitionException(data_format, err)


def compare_json_helper(item):
    if isinstance(item, dict):
        return sorted(
            (key, compare_json_helper(values)) for key, values in item.items()
        )
    if isinstance(item, list):
        return sorted(compare_json_helper(x) for x in item)
    else:
        return item


def compare_json(a, b):
    return compare_json_helper(a) == compare_json_helper(b)


def validate_registry_id(registry_id, registries):
    if not registry_id:
        registry_name = DEFAULT_REGISTRY_NAME
        return registry_name

    elif registry_id.get(REGISTRY_NAME) and registry_id.get(REGISTRY_ARN):
        raise InvalidRegistryIdBothParamsProvidedException()

    if registry_id.get(REGISTRY_NAME):
        registry_name = registry_id.get(REGISTRY_NAME)
        validate_registry_name_pattern_and_length(registry_name)

    elif registry_id.get(REGISTRY_ARN):
        registry_arn = registry_id.get(REGISTRY_ARN)
        validate_arn_pattern_and_length(registry_arn)
        registry_name = registry_arn.split("/")[-1]

    if registry_name not in registries:
        if registry_id.get(REGISTRY_NAME):
            raise GSREntityNotFoundException(
                resource="Registry",
                param_name=REGISTRY_NAME,
                param_value=registry_name,
            )
        if registry_id.get(REGISTRY_ARN):
            raise GSREntityNotFoundException(
                resource="Registry",
                param_name=REGISTRY_ARN,
                param_value=registry_arn,
            )

    return registry_name


def validate_registry_params(registries, registry_name, description=None, tags=None):
    if len(registries) >= MAX_REGISTRIES_ALLOWED:
        raise ResourceNumberLimitExceededException(resource="registries")

    validate_registry_name_pattern_and_length(registry_name)

    if registry_name in registries:
        raise GSRAlreadyExistsException(
            resource="Registry",
            param_name=REGISTRY_NAME,
            param_value=registry_name,
        )

    if description:
        validate_description_pattern_and_length(description)

    if tags:
        validate_number_of_tags(tags)


def validate_schema_id(schema_id, registries):
    if schema_id:
        schema_arn = schema_id.get(SCHEMA_ARN)
        registry_name = schema_id.get(REGISTRY_NAME)
        schema_name = schema_id.get(SCHEMA_NAME)
        if schema_arn:
            if registry_name or schema_name:
                raise InvalidSchemaIdBothParamsProvidedException()
            validate_arn_pattern_and_length(schema_arn)
            arn_components = schema_arn.split("/")
            schema_name = arn_components[-1]
            registry_name = arn_components[-2]

        else:
            if registry_name is None or schema_name is None:
                raise InvalidSchemaIdInsufficientParamsProvidedException()
            validate_registry_name_pattern_and_length(registry_name)
            validate_schema_name_pattern_and_length(schema_name)

    if (
        registry_name not in registries
        or schema_name not in registries[registry_name].schemas
    ):
        raise SchemaNotFoundException()

    return registry_name, schema_name


def validate_schema_params(
    registry,
    schema_name,
    data_format,
    compatibility,
    schema_definition,
    num_schemas,
    description=None,
    tags=None,
):
    validate_schema_name_pattern_and_length(schema_name)

    if num_schemas >= MAX_SCHEMAS_ALLOWED:
        raise ResourceNumberLimitExceededException(resource="schemas")

    if data_format not in ["AVRO", "JSON", "PROTOBUF"]:
        raise InvalidDataFormatException()

    if compatibility not in [
        "NONE",
        "DISABLED",
        "BACKWARD",
        "BACKWARD_ALL",
        "FORWARD",
        "FORWARD_ALL",
        "FULL",
        "FULL_ALL",
    ]:
        raise InvalidCompatibilityException()

    if description:
        validate_description_pattern_and_length(description)

    if tags:
        validate_number_of_tags(tags)

    if len(schema_definition) > MAX_SCHEMA_DEFINITION_LENGTH:
        param_name = SCHEMA_DEFINITION
        raise ResourceNameTooLongException(param_name)

    if schema_name in registry.schemas:
        raise GSRAlreadyExistsException(
            resource="Schema",
            param_name=SCHEMA_NAME,
            param_value=schema_name,
        )

    validate_avro_json_schema_definition(data_format, schema_definition)


def validate_schema_version_params(
    registry_name,
    schema_name,
    num_schema_versions,
    schema_definition,
    compatibility,
    data_format,
):
    if num_schema_versions >= MAX_SCHEMA_VERSIONS_ALLOWED:
        raise ResourceNumberLimitExceededException(resource="schema versions")

    if len(schema_definition) > MAX_SCHEMA_DEFINITION_LENGTH:
        param_name = SCHEMA_DEFINITION
        raise ResourceNameTooLongException(param_name)

    if compatibility == "DISABLED":
        raise DisabledCompatibilityVersioningException(schema_name, registry_name)

    validate_avro_json_schema_definition(data_format, schema_definition)


def get_schema_version_if_definition_exists(
    schema_versions, data_format, schema_definition
):
    if data_format in ["AVRO", "JSON"]:
        for schema_version in schema_versions:
            if compare_json(schema_definition, schema_version.schema_definition):
                return schema_version.as_dict()
    else:
        for schema_version in schema_versions:
            if schema_definition == schema_version.schema_definition:
                return schema_version.as_dict()
    return None
