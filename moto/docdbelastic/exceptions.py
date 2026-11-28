"""Exceptions raised by the docdb-elastic service."""

from moto.core.exceptions import ServiceException


class ResourceNotFoundException(ServiceException):
    code = "ResourceNotFoundException"

    def __init__(self, resource_id: str, resource_type: str):
        self.resource_id = resource_id
        self.resource_type = resource_type
        super().__init__(f"{resource_type} {resource_id} not found")


class ConflictException(ServiceException):
    code = "ConflictException"

    def __init__(self, message: str, resource_id: str, resource_type: str):
        self.resource_id = resource_id
        self.resource_type = resource_type
        super().__init__(message)


class ValidationException(ServiceException):
    code = "ValidationException"

    def __init__(self, message: str, reason: str = "other"):
        self.reason = reason
        super().__init__(message)
