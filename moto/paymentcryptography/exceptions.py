"""Exceptions raised by the paymentcryptography service."""
from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    def __init__(self, msg: str):
        super().__init__("ResourceNotFoundException", f"{msg}")


class ConflictException(JsonRESTError):
    def __init__(self, msg: str):
        super().__init__("ConflictException", f"{msg}")
