"""Handles incoming directconnect requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import Connection, DirectConnectBackend, directconnect_backends


class DirectConnectResponse(BaseResponse):
    """Handler for DirectConnect requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="directconnect")

    @property
    def directconnect_backend(self) -> DirectConnectBackend:
        return directconnect_backends[self.current_account][self.region]

    def describe_connections(self) -> str:
        params = json.loads(self.body)
        connections = self.directconnect_backend.describe_connections(
            connection_id=params.get("connectionId"),
        )
        return json.dumps(
            dict(connections=[connection.to_dict() for connection in connections])
        )

    def create_connection(self) -> str:
        params = json.loads(self.body)
        connection: Connection = self.directconnect_backend.create_connection(
            location=params.get("location"),
            bandwidth=params.get("bandwidth"),
            connection_name=params.get("connectionName"),
            lag_id=params.get("lagId"),
            tags=params.get("tags"),
            provider_name=params.get("providerName"),
            request_mac_sec=params.get("requestMACSec"),
        )
        return json.dumps(connection.to_dict())

    def delete_connection(self) -> str:
        params = json.loads(self.body)
        connection: Connection = self.directconnect_backend.delete_connection(
            connection_id=params.get("connectionId"),
        )
        return json.dumps(connection.to_dict())

    def update_connection(self) -> str:
        params = json.loads(self.body)
        connection: Connection = self.directconnect_backend.update_connection(
            connection_id=params.get("connectionId"),
            new_connection_name=params.get("connectionName"),
            new_encryption_mode=params.get("encryptionMode"),
        )
        return json.dumps(connection.to_dict())
