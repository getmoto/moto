"""Exceptions raised by the cloudhsmv2 service."""

from moto.core.exceptions import ServiceException


class CloudHSMv2ClientError(ServiceException):
    """Base class for CloudHSMv2 errors."""


class ResourceNotFoundException(CloudHSMv2ClientError):
    code = "CloudHsmResourceNotFoundException"


class InvalidRequestException(CloudHSMv2ClientError):
    code = "CloudHsmInvalidRequestException"
