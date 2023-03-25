"""Exceptions raised by the opensearch service."""
from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    def __init__(self, name: str):
        super().__init__("ResourceNotFoundException", f"Domain not found: {name}")
