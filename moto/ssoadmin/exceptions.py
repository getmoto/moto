"""Exceptions raised by the ssoadmin service."""
from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    def __init__(self, message: str = "Account not found") -> None:
        super().__init__(
            error_type="ResourceNotFoundException",
            message=message,
            code="ResourceNotFoundException",
        )
