"""BedrockAgentCore exceptions."""

from moto.core.exceptions import ServiceException


class BedrockAgentCoreClientError(ServiceException):
    pass


class ResourceNotFoundException(BedrockAgentCoreClientError):
    code = "ResourceNotFoundException"


class ValidationException(BedrockAgentCoreClientError):
    code = "ValidationException"
