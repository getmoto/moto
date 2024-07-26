"""Exceptions raised by the transfer service."""
from moto.core.exceptions import JsonRESTError

class TransferError(JsonRESTError):
    code = 400

class ServerNotFound(TransferError):
    def __init__(self, server_id: str) -> None:
        super().__init__(
            "ServerNotFound",
            f"There are no transfer protocol-enabled servers with ID {server_id}."
        ) 

class UserNotFound(TransferError):
    def __init__(self, user_name: str) -> None:
        super().__init__(
            "UserNotFound",
            f"{user_name} does not match any user associated with a transfer protocol-enabled server."
        )

class ServerNotAssociatedWithUser(TransferError):
    def __init__(self, user_name: str, server_id: str) -> None:
        super().__init__(
            "ServerNotAssociatedWithUser",
            f"{user_name} does not match any user associated with server {server_id}."
        )