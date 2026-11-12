"""Exceptions raised by the identitystore service."""

from moto.core.exceptions import ServiceException

# TODO: Get rid of this hardcoded id in favor of something in core.
request_id = "178936da-50ad-4d58-8871-22d9979e8658example"


class IdentityStoreError(ServiceException):
    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        reason: str | None = None,
    ):
        super().__init__(message)
        self.request_id = request_id
        self.resource_type = resource_type
        self.reason = reason


class ResourceNotFoundException(IdentityStoreError):
    code = "ResourceNotFoundException"


class ValidationException(IdentityStoreError):
    code = "ValidationException"


class ConflictException(IdentityStoreError):
    code = "ConflictException"
