"""Exceptions raised by the ssoadmin service."""
from moto.core.exceptions import JsonRESTError


class ResourceNotFound(JsonRESTError):
    def __init__(self) -> None:
        super().__init__("ResourceNotFound", "Account not found")
