"""Exceptions raised by the cleanrooms service."""

import json

from moto.core.exceptions import JsonRESTError


class CleanRoomsException(JsonRESTError):
    pass


class ResourceNotFoundException(CleanRoomsException):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            "ResourceNotFoundException",
            f"Could not find {resource_type} with id {resource_id}",
        )
        self.description = json.dumps({"message": self.message})
