"""Handles incoming directconnect requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse

from .models import Connection, directconnect_backends


class DirectConnectResponse(BaseResponse):
    """Handler for DirectConnect requests and responses."""

    def __init__(self):
        super().__init__(service_name="directconnect")

    @property
    def directconnect_backend(self):
        """Return backend instance specific for this region."""
        return directconnect_backends[self.current_account][self.region]
    
    def describe_connections(self) -> str:
        params = json.loads(self.body)
        connections = self.directconnect_backend.describe_connections(
            connection_id=params.get("connectionId"),
        )
        return json.dumps(dict(connections=connections))
    
    def create_connection(self):
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
    
    def delete_connection(self):
        params = json.loads(self.body)
        connection: Connection = self.directconnect_backend.delete_connection(
            connection_id=params.get("connectionId"),
        )
        return json.dumps(connection.to_dict())
    
    def update_connection(self):
        params = self._get_params()
        connection: Connection = self.directconnect_backend.update_connection(
            connection_id=params.get("connectionId"),
            connection_name=params.get("connectionName"),
            encryption_mode=params.get("encryptionMode"),
        )
        return json.dumps(connection.to_dict())
