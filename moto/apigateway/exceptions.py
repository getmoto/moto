from __future__ import unicode_literals
from moto.core.exceptions import JsonRESTError


class BadRequestException(JsonRESTError):
    pass


class NotFoundException(JsonRESTError):
    pass


class AccessDeniedException(JsonRESTError):
    pass


class AwsProxyNotAllowed(BadRequestException):
    def __init__(self):
        super(AwsProxyNotAllowed, self).__init__(
            "BadRequestException",
            "Integrations of type 'AWS_PROXY' currently only supports Lambda function and Firehose stream invocations.",
        )


class CrossAccountNotAllowed(AccessDeniedException):
    def __init__(self):
        super(CrossAccountNotAllowed, self).__init__(
            "AccessDeniedException", "Cross-account pass role is not allowed."
        )


class RoleNotSpecified(BadRequestException):
    def __init__(self):
        super(RoleNotSpecified, self).__init__(
            "BadRequestException", "Role ARN must be specified for AWS integrations"
        )


class IntegrationMethodNotDefined(BadRequestException):
    def __init__(self):
        super(IntegrationMethodNotDefined, self).__init__(
            "BadRequestException", "Enumeration value for HttpMethod must be non-empty"
        )


class InvalidResourcePathException(BadRequestException):
    def __init__(self):
        super(InvalidResourcePathException, self).__init__(
            "BadRequestException",
            "Resource's path part only allow a-zA-Z0-9._- and curly braces at the beginning and the end and an optional plus sign before the closing brace.",
        )


class InvalidHttpEndpoint(BadRequestException):
    def __init__(self):
        super(InvalidHttpEndpoint, self).__init__(
            "BadRequestException", "Invalid HTTP endpoint specified for URI"
        )


class InvalidArn(BadRequestException):
    def __init__(self):
        super(InvalidArn, self).__init__(
            "BadRequestException", "Invalid ARN specified in the request"
        )


class InvalidIntegrationArn(BadRequestException):
    def __init__(self):
        super(InvalidIntegrationArn, self).__init__(
            "BadRequestException", "AWS ARN for integration must contain path or action"
        )


class InvalidRequestInput(BadRequestException):
    def __init__(self):
        super(InvalidRequestInput, self).__init__(
            "BadRequestException", "Invalid request input"
        )


class NoIntegrationDefined(NotFoundException):
    def __init__(self):
        super(NoIntegrationDefined, self).__init__(
            "NotFoundException", "No integration defined for method"
        )


class NoIntegrationResponseDefined(NotFoundException):
    code = 404

    def __init__(self, code=None):
        super(NoIntegrationResponseDefined, self).__init__(
            "NotFoundException", "Invalid Response status code specified"
        )


class NoMethodDefined(BadRequestException):
    def __init__(self):
        super(NoMethodDefined, self).__init__(
            "BadRequestException", "The REST API doesn't contain any methods"
        )


class AuthorizerNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super(AuthorizerNotFoundException, self).__init__(
            "NotFoundException", "Invalid Authorizer identifier specified"
        )


class StageNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super(StageNotFoundException, self).__init__(
            "NotFoundException", "Invalid stage identifier specified"
        )


class ApiKeyNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super(ApiKeyNotFoundException, self).__init__(
            "NotFoundException", "Invalid API Key identifier specified"
        )


class UsagePlanNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super(UsagePlanNotFoundException, self).__init__(
            "NotFoundException", "Invalid Usage Plan ID specified"
        )


class ApiKeyAlreadyExists(JsonRESTError):
    code = 409

    def __init__(self):
        super(ApiKeyAlreadyExists, self).__init__(
            "ConflictException", "API Key already exists"
        )


class InvalidDomainName(BadRequestException):
    code = 404

    def __init__(self):
        super(InvalidDomainName, self).__init__(
            "BadRequestException", "No Domain Name specified"
        )


class DomainNameNotFound(NotFoundException):
    code = 404

    def __init__(self):
        super(DomainNameNotFound, self).__init__(
            "NotFoundException", "Invalid domain name identifier specified"
        )


class InvalidRestApiId(BadRequestException):
    code = 404

    def __init__(self):
        super(InvalidRestApiId, self).__init__(
            "BadRequestException", "No Rest API Id specified"
        )


class InvalidModelName(BadRequestException):
    code = 404

    def __init__(self):
        super(InvalidModelName, self).__init__(
            "BadRequestException", "No Model Name specified"
        )


class RestAPINotFound(NotFoundException):
    code = 404

    def __init__(self):
        super(RestAPINotFound, self).__init__(
            "NotFoundException", "Invalid Rest API Id specified"
        )


class ModelNotFound(NotFoundException):
    code = 404

    def __init__(self):
        super(ModelNotFound, self).__init__(
            "NotFoundException", "Invalid Model Name specified"
        )


class ApiKeyValueMinLength(BadRequestException):
    code = 400

    def __init__(self):
        super(ApiKeyValueMinLength, self).__init__(
            "BadRequestException", "API Key value should be at least 20 characters"
        )


class MethodNotFoundException(NotFoundException):
    code = 404

    def __init__(self):
        super(MethodNotFoundException, self).__init__(
            "NotFoundException", "Invalid method properties specified"
        )
