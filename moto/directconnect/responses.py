"""Handles incoming directconnect requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import directconnect_backends


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
        connection_id = params.get("connectionId")
        connections = self.directconnect_backend.describe_connections(
            connection_id=connection_id,
        )
        return json.dumps(dict(connections=connections))
