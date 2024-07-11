"""Exceptions raised by the directconnect service."""

from moto.core.exceptions import JsonRESTError


class DXConnectionError(JsonRESTError):
    code = 400


class ConnectionIdMissing(DXConnectionError):
    def __init__(self) -> None:
        super().__init__("ConnectionIdMissing", "The connection ID is missing.")


class ConnectionNotFound(DXConnectionError):
    def __init__(self, connnection_id: str, region: str) -> None:
        super().__init__(
            "ConnectionNotFound",
            f"{connnection_id} does not match any connections in region {region}.",
        )
