from moto.core.exceptions import JsonRESTError


class BadRequestException(JsonRESTError):
    pass


class NotFoundException(JsonRESTError):
    pass


class AccessDeniedException(JsonRESTError):
    pass


class ConflictException(JsonRESTError):
    code = 409


class AwsProxyNotAllowed(BadRequestException):
    def __init__(self):
        super().__init__(
            "BadRequestException",
            "Integrations of type 'AWS_PROXY' currently only supports Lambda function and Firehose stream invocations.",
        )


class CrossAccountNotAllowed(AccessDeniedException):
    def __init__(self):
        super().__init__(
            "AccessDeniedException", "Cross-account pass role is not allowed."
        )


class RoleNotSpecified(BadRequestException):
    def __init__(self):
        super().__init__(
            "BadRequestException", "Role ARN must be specified for AWS integrations"
        )


class IntegrationMethodNotDefined(BadRequestException):
    def __init__(self):
        super().__init__(
            "BadRequestException", "Enumeration value for HttpMethod must be non-empty"
        )


class InvalidResourcePathException(BadRequestException):
    def __init__(self):
        super().__init__(
            "BadRequestException",
            "Resource's path part only allow a-zA-Z0-9._- and curly braces at the beginning and the end and an optional plus sign before the closing brace.",
        )


class InvalidHttpEndpoint(BadRequestException):
    def __init__(self):
        super().__init__(
            "BadRequestException", "Invalid HTTP endpoint specified for URI"
        )


class InvalidArn(BadRequestException):
    def __init__(self):
        super().__init__("BadRequestException", "Invalid ARN specified in the request")


class InvalidIntegrationArn(BadRequestException):
    def __init__(self):
        super().__init__(
            "BadRequestException", "AWS ARN for integration must contain path or action"
        )


class InvalidRequestInput(BadRequestException):
    def __init__(self):
        super().__init__("BadRequestException", "Invalid request input")


class NoIntegrationDefined(NotFoundException):
    def __init__(self):
        super().__init__("NotFoundException", "No integration defined for method")


class NoIntegrationResponseDefined(NotFoundException):
    code = 404

    def __init__(self, code=None):
        super().__init__("NotFoundException", "Invalid Response status code specified")


class NoMethodDefined(BadRequestException):
    def __init__(self):
        super().__init__(
            "BadRequestException", "The REST API doesn't contain any methods"
        )


class AuthorizerNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__("NotFoundException", "Invalid Authorizer identifier specified")


class StageNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__("NotFoundException", "Invalid stage identifier specified")


class ApiKeyNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__("NotFoundException", "Invalid API Key identifier specified")


class UsagePlanNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__("NotFoundException", "Invalid Usage Plan ID specified")


class ApiKeyAlreadyExists(JsonRESTError):
    code = 409

    def __init__(self):
        super().__init__("ConflictException", "API Key already exists")


class InvalidDomainName(BadRequestException):
    code = 404

    def __init__(self):
        super().__init__("BadRequestException", "No Domain Name specified")


class DomainNameNotFound(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__(
            "NotFoundException", "Invalid domain name identifier specified"
        )


class InvalidRestApiId(BadRequestException):
    code = 404

    def __init__(self):
        super().__init__("BadRequestException", "No Rest API Id specified")


class InvalidModelName(BadRequestException):
    code = 404

    def __init__(self):
        super().__init__("BadRequestException", "No Model Name specified")


class RestAPINotFound(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__("NotFoundException", "Invalid Rest API Id specified")


class RequestValidatorNotFound(BadRequestException):
    code = 400

    def __init__(self):
        super().__init__("NotFoundException", "Invalid Request Validator Id specified")


class ModelNotFound(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__("NotFoundException", "Invalid Model Name specified")


class ApiKeyValueMinLength(BadRequestException):
    code = 400

    def __init__(self):
        super().__init__(
            "BadRequestException", "API Key value should be at least 20 characters"
        )


class MethodNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__("NotFoundException", "Invalid Method identifier specified")


class InvalidBasePathException(BadRequestException):
    code = 400

    def __init__(self):
        super().__init__(
            "BadRequestException",
            "API Gateway V1 doesn't support the slash character (/) in base path mappings. "
            "To create a multi-level base path mapping, use API Gateway V2.",
        )


class InvalidRestApiIdForBasePathMappingException(BadRequestException):
    code = 400

    def __init__(self):
        super().__init__("BadRequestException", "Invalid REST API identifier specified")


class InvalidStageException(BadRequestException):
    code = 400

    def __init__(self):
        super().__init__("BadRequestException", "Invalid stage identifier specified")


class BasePathConflictException(ConflictException):
    def __init__(self):
        super().__init__(
            "ConflictException", "Base path already exists for this domain name"
        )


class BasePathNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super().__init__(
            "NotFoundException", "Invalid base path mapping identifier specified"
        )
