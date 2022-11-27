"""Exceptions raised by the acmpca service."""
from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    def __init__(self, arn: str):
        super().__init__("ResourceNotFoundException", f"Resource {arn} not found")
