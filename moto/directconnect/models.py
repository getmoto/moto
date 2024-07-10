"""DirectConnectBackend class with methods for supported APIs."""

from dataclasses import dataclass
from datetime import datetime
from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from typing import Dict, List
from moto.directconnect.enums import ConnectionStateType, EncryptionModeType, MacSecKeyStateType, PortEncryptionStatusType

@dataclass
class MacSecKey(BaseModel):
    secret_arn: str
    ckn: str
    state: MacSecKeyStateType
    start_on: str

    def to_dict(self):
        return {
            "secretARN": self.secret_arn,
            "ckn": self.ckn,
            "state": self.state,
            "startOn": self.start_on
        }

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
    loa_issue_time: datetime
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
    mac_sec_keys: List[MacSecKey]

    def to_dict(self):
        return {
            "connectionId": self.connection_id,
            "connectionName": self.connection_name,
            "connectionState": self.connection_state,
            "region": self.region,
            "location": self.location,
            "bandwidth": self.bandwidth,
            "vlan": self.vlan,
            "partnerName": self.partner_name,
            "loaIssueTime": self.loa_issue_time,
            "lagId": self.lag_id,
            "awsDevice": self.aws_device,
            "jumboFrameCapable": self.jumbo_frame_capable,
            "awsDeviceV2": self.aws_device_v2,
            "awsLogicalDeviceId": self.aws_logical_device_id,
            "hasLogicalRedundancy": self.has_logical_redundancy,
            "tags": self.tags,
            "providerName": self.provider_name,
            "macSecCapable": self.mac_sec_capable,
            "portEncryptionStatus": self.port_encryption_status,
            "encryptionMode": self.encryption_mode,
            "macSecKeys": [key.to_dict() for key in self.mac_sec_keys]
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
