"""DirectConnectBackend class with methods for supported APIs."""

from dataclasses import dataclass
from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from typing import Dict
from utils import ConnectionStateType, EncryptionModeType, PortEncryptionStatusType

@dataclass
class Connection(BaseModel):
    connection_id: str
    owner_account: str
    connection_name: str
    connection_state: ConnectionStateType = ConnectionStateType.AVAILABLE
    region: str
    location: str
    bandwidth: str
    vlan: int
    partner_name: str
    loa_issue_time: str # TODO: datetime
    lag_id: str
    aws_device: str
    jumbo_frame_capable: bool
    aws_device_v2: str
    aws_logical_device_id: str
    has_logical_redundancy: bool
    tags: Dict[str, str]
    provider_name: str
    mac_sec_capable: bool
    port_encryption_status: PortEncryptionStatusType
    encryption_mode: EncryptionModeType
    mac_sec_keys: Dict[str, str] # TODO dataclass

    def to_dict(self):
        return {
            "connectionId": self.connection_id,
            "connectionName": self.connection_name,
            # TODO remaining fields
        }

class DirectConnectBackend(BaseBackend):
    """Implementation of DirectConnect APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.connections: Dict[str, Connection] = {}

    def describe_connections(self, connection_id: str) -> Connection:
        if connection_id:
            return self.connections.get(connection_id)
        return self.connections.values()
    
    # TODO: create_connection, delete_connection, update_connection, etc.
    

directconnect_backends = BackendDict(DirectConnectBackend, "directconnect")
