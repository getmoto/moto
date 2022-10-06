"""Exceptions raised by the comprehend service."""
from moto.core.exceptions import JsonRESTError


class ResourceNotFound(JsonRESTError):
    def __init__(self):
        super().__init__(
            "ResourceNotFoundException",
            "RESOURCE_NOT_FOUND: Could not find specified resource.",
        )
