"""Exceptions raised by the transfer service."""
from moto.core.exceptions import JsonRESTError

class TransferError(JsonRESTError):
    code = 400

class UserNotFound(TransferError):
    def __init__(self, user_name: str) -> None:
        super().__init__(
            "UserNotFound",
            f"{user_name} does not match any user associated with an FTP-enabled server."
        )