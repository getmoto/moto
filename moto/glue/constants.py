import re

# This file contains the constants required for Glue Schema Registry APIs.

# common used constants
MAX_DESCRIPTION_LENGTH = 2048
MAX_ARN_LENGTH = 1000
MAX_TAGS_ALLOWED = 50
RESOURCE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-_$#.]+$")
DESCRIPTION_PATTERN = re.compile(
    r"[\\u0020-\\uD7FF\\uE000-\\uFFFD\\uD800\\uDC00-\\uDBFF\\uDFFF\\r\\n\\t]*"
)
ARN_PATTERN = re.compile(r"^arn:(aws|aws-us-gov|aws-cn):glue:.*$")
SCHEMA_VERSION_ID_PATTERN = re.compile(
    r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
)

# registry constants
MAX_REGISTRY_NAME_LENGTH = 255
MAX_REGISTRIES_ALLOWED = 10
CREATE_REGISTRY_OPERATION_NAME = "CreateRegistry"
DEFAULT_REGISTRY_NAME = "default-registry"

# schema constants
MAX_SCHEMA_NAME_LENGTH = 255
MAX_SCHEMAS_ALLOWED = 1000
CREATE_SCHEMA_OPERATION_NAME = "CreateSchema"
MAX_SCHEMA_DEFINITION_LENGTH = 170000

# schema version number constants
MAX_VERSION_NUMBER = 100000
MAX_SCHEMA_VERSIONS_ALLOWED = 1000
REGISTER_SCHEMA_VERSION_OPERATION_NAME = "RegisterSchemaVersion"
