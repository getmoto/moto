"""Exceptions raised by the shield service."""

from moto.core.exceptions import ServiceException


class ShieldException(ServiceException):
    pass


class ResourceAlreadyExistsException(ShieldException):
    code = "ResourceAlreadyExistsException"


class InvalidResourceException(ShieldException):
    code = "InvalidResourceException"


class InvalidParameterException(ShieldException):
    code = "InvalidParameterException"


class ResourceNotFoundException(ShieldException):
    code = "ResourceNotFoundException"


class ValidationException(ShieldException):
    code = "ValidationException"
