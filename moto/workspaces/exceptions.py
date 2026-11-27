"""Exceptions raised by the workspaces service."""

from moto.core.exceptions import ServiceException


class WorkSpacesException(ServiceException):
    pass


class ValidationException(WorkSpacesException):
    code = "ValidationException"


class InvalidParameterValuesException(WorkSpacesException):
    code = "InvalidParameterValuesException"


class ResourceAlreadyExistsException(WorkSpacesException):
    code = "ResourceAlreadyExistsException"


class ResourceNotFoundException(WorkSpacesException):
    code = "ResourceNotFoundException"
