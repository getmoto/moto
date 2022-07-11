from moto.core.exceptions import JsonRESTError


class GlueClientError(JsonRESTError):
    code = 400


class AlreadyExistsException(GlueClientError):
    def __init__(self, typ):
        super().__init__("AlreadyExistsException", "%s already exists." % (typ))


class DatabaseAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Database")


class TableAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Table")


class PartitionAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Partition")


class CrawlerAlreadyExistsException(AlreadyExistsException):
    def __init__(self):
        super().__init__("Crawler")


class EntityNotFoundException(GlueClientError):
    def __init__(self, msg):
        super().__init__("EntityNotFoundException", msg)


class DatabaseNotFoundException(EntityNotFoundException):
    def __init__(self, db):
        super().__init__("Database %s not found." % db)


class TableNotFoundException(EntityNotFoundException):
    def __init__(self, tbl):
        super().__init__("Table %s not found." % tbl)


class PartitionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super().__init__("Cannot find partition.")


class CrawlerNotFoundException(EntityNotFoundException):
    def __init__(self, crawler):
        super().__init__("Crawler %s not found." % crawler)


class JobNotFoundException(EntityNotFoundException):
    def __init__(self, job):
        super().__init__("Job %s not found." % job)


class VersionNotFoundException(EntityNotFoundException):
    def __init__(self):
        super().__init__("Version not found.")


class SchemaNotFoundException(EntityNotFoundException):
    def __init__(self):
        super().__init__(
            "Schema is not found.",
        )


class GSREntityNotFoundException(EntityNotFoundException):
    def __init__(self, resource, param_name, param_value):
        super().__init__(
            resource + " is not found. " + param_name + ": " + param_value,
        )


class CrawlerRunningException(GlueClientError):
    def __init__(self, msg):
        super().__init__("CrawlerRunningException", msg)


class CrawlerNotRunningException(GlueClientError):
    def __init__(self, msg):
        super().__init__("CrawlerNotRunningException", msg)


class ConcurrentRunsExceededException(GlueClientError):
    def __init__(self, msg):
        super().__init__("ConcurrentRunsExceededException", msg)


class ResourceNumberLimitExceededException(GlueClientError):
    def __init__(self, resource):
        super().__init__(
            "ResourceNumberLimitExceededException",
            "More "
            + resource
            + " cannot be created. The maximum limit has been reached.",
        )


class GSRAlreadyExistsException(GlueClientError):
    def __init__(self, resource, param_name, param_value):
        super().__init__(
            "AlreadyExistsException",
            resource + " already exists. " + param_name + ": " + param_value,
        )


class _InvalidOperationException(GlueClientError):
    def __init__(self, error_type, op, msg):
        super().__init__(
            error_type,
            "An error occurred (%s) when calling the %s operation: %s"
            % (error_type, op, msg),
        )


class InvalidStateException(_InvalidOperationException):
    def __init__(self, op, msg):
        super().__init__("InvalidStateException", op, msg)


class InvalidInputException(_InvalidOperationException):
    def __init__(self, op, msg):
        super().__init__("InvalidInputException", op, msg)


class GSRInvalidInputException(GlueClientError):
    def __init__(self, msg):
        super().__init__("InvalidInputException", msg)


class ResourceNameTooLongException(GSRInvalidInputException):
    def __init__(self, param_name):
        super().__init__(
            "The resource name contains too many or too few characters. Parameter Name: "
            + param_name,
        )


class ParamValueContainsInvalidCharactersException(GSRInvalidInputException):
    def __init__(self, param_name):
        super().__init__(
            "The parameter value contains one or more characters that are not valid. Parameter Name: "
            + param_name,
        )


class InvalidNumberOfTagsException(GSRInvalidInputException):
    def __init__(self):
        super().__init__(
            "New Tags cannot be empty or more than 50",
        )


class InvalidDataFormatException(GSRInvalidInputException):
    def __init__(self):
        super().__init__(
            "Data format is not valid.",
        )


class InvalidCompatibilityException(GSRInvalidInputException):
    def __init__(self):
        super().__init__(
            "Compatibility is not valid.",
        )


class InvalidSchemaDefinitionException(GSRInvalidInputException):
    def __init__(self, data_format_name, err):
        super().__init__(
            "Schema definition of "
            + data_format_name
            + " data format is invalid: "
            + str(err),
        )


class InvalidRegistryIdBothParamsProvidedException(GSRInvalidInputException):
    def __init__(self):
        super().__init__(
            "One of registryName or registryArn has to be provided, both cannot be provided.",
        )


class InvalidSchemaIdBothParamsProvidedException(GSRInvalidInputException):
    def __init__(self):
        super().__init__(
            "One of (registryName and schemaName) or schemaArn has to be provided, both cannot be provided.",
        )


class InvalidSchemaIdInsufficientParamsProvidedException(GSRInvalidInputException):
    def __init__(self):
        super().__init__(
            "At least one of (registryName and schemaName) or schemaArn has to be provided.",
        )


class DisabledCompatibilityVersioningException(GSRInvalidInputException):
    def __init__(self, schema_name, registry_name):
        super().__init__(
            "Compatibility DISABLED does not allow versioning. SchemaId: SchemaId(schemaName="
            + schema_name
            + ", registryName="
            + registry_name
            + ")"
        )
