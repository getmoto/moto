"""Exceptions raised by the directconnect service."""

from moto.core.exceptions import ServiceException


class DXConnectionError(ServiceException):
    pass


class ConnectionIdMissing(DXConnectionError):
    code = "DirectConnectClientException"
    message = "The connection ID is missing."


class ConnectionNotFound(DXConnectionError):
    code = "DirectConnectClientException"

    def __init__(self, connection_id: str, region: str) -> None:
        super().__init__(
            f"{connection_id} does not match any connections in region {region}."
        )


class LAGNotFound(DXConnectionError):
    code = "DirectConnectClientException"

    def __init__(self, lag_id: str, region: str) -> None:
        super().__init__(f"{lag_id} does not match any LAGs in region {region}.")


class MacSecKeyNotFound(DXConnectionError):
    code = "DirectConnectClientException"

    def __init__(self, secret_arn: str, connection_id: str) -> None:
        super().__init__(
            f"Secret ARN '{secret_arn}' not found for connection {connection_id}."
        )
