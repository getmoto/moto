"""Exceptions raised by the paymentcryptography service."""

from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    code = 404

    def __init__(self, msg: str):
        super().__init__("ResourceNotFoundException", f"{msg}")


class ConflictException(JsonRESTError):
    code = 409

    def __init__(self, msg: str):
        super().__init__("ConflictException", f"{msg}")
