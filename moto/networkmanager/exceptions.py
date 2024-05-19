"""Exceptions raised by the networkmanager service."""

from moto.core.exceptions import JsonRESTError


class ValidationError(JsonRESTError):
    def __init__(self, message: str):
        super().__init__("ValidationException", message)


class ResourceNotFound(JsonRESTError):
    def __init__(self, message: str):
        super().__init__(__class__.__name__, message)  # type: ignore
