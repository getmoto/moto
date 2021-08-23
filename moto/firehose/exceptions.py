"""Exceptions raised by the AWS Firehose service."""
from moto.core.exceptions import JsonRESTError


class NameTooLongException(JsonRESTError):
    code = 400

    def __init__(self, name, location, max_limit=256):
        message = (
            f"1 validation error detected: Value '{name}' at '{location}' "
            f"failed to satisfy constraint: Member must have length less "
            f"than or equal to {max_limit}"
        )
        super().__init__("ValidationException", message)
