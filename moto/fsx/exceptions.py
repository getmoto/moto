"""Exceptions raised by the fsx service."""

from moto.core.exceptions import JsonRESTError


class ResourceNotFoundException(JsonRESTError):
    def __init__(self, msg: str):
        super().__init__("ResourceNotFoundException", f"{msg}")


class FileSystemNotFound(JsonRESTError):
    def __init__(self, file_system_id: str):
        super().__init__(
            "FileSystemNotFound", f"File system '{file_system_id}' does not exist."
        )
