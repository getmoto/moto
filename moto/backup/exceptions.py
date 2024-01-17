"""Exceptions raised by the backup service."""
from moto.core.exceptions import JsonRESTError

class BackupClientError(JsonRESTError):
    code = 400

class AlreadyExistsException(BackupClientError):
    def __init__(self, name: str):
        super().__init__("AlreadyExistsException", f"{name} already exists.")

class ResourceNotFoundException(JsonRESTError):
    def __init__(self, name: str):
        super().__init__("ResourceNotFoundException", f"An error occurred (ResourceNotFoundException) when calling the GetBackupPlan operation: Failed reading Backup plan with provided version")