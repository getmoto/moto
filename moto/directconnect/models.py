"""DirectConnectBackend class with methods for supported APIs."""

from .enums import ConnectionStateType, EncryptionModeType, MacSecKeyStateType, PortEncryptionStatusType
from dataclasses import dataclass
from datetime import datetime
from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from typing import Dict, List

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
    aws_device_v2: str
    aws_device: str
    aws_logical_device_id: str
    bandwidth: str
    connection_id: str = f"dx-moto{datetime.now().strftime('%Y%m%d%H%M%S')}"
    connection_name: str
    connection_state: ConnectionStateType
    encryption_mode: EncryptionModeType
    has_logical_redundancy: bool
    jumbo_frame_capable: bool
    lag_id: str
    loa_issue_time: datetime
    location: str
    mac_sec_capable: bool
    mac_sec_keys: List[MacSecKey]
    owner_account: str
    partner_name: str
    port_encryption_status: PortEncryptionStatusType
    provider_name: str
    region: str
    tags: Dict[str, str]
    vlan: int

    def to_dict(self):
        return {
            "awsDevice": self.aws_device,
            "awsDeviceV2": self.aws_device_v2,
            "awsLogicalDeviceId": self.aws_logical_device_id,
            "bandwidth": self.bandwidth,
            "connectionId": self.connection_id,
            "connectionName": self.connection_name,
            "connectionState": self.connection_state,
            "encryptionMode": self.encryption_mode,
            "hasLogicalRedundancy": self.has_logical_redundancy,
            "jumboFrameCapable": self.jumbo_frame_capable,
            "lagId": self.lag_id,
            "loaIssueTime": self.loa_issue_time,
            "location": self.location,
            "macSecCapable": self.mac_sec_capable,
            "macSecKeys": [key.to_dict() for key in self.mac_sec_keys],
            "partnerName": self.partner_name,
            "portEncryptionStatus": self.port_encryption_status,
            "providerName": self.provider_name,
            "region": self.region,
            "tags": self.tags,
            "vlan": self.vlan,
        }

class DirectConnectBackend(BaseBackend):
    """Implementation of DirectConnect APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.connections: Dict[str, Connection] = {}

    def describe_connections(self, connection_id: str) -> List[Connection]:
        if connection_id:
            return list(self.connections.get(connection_id))
        return self.connections.values()
        
    def create_connection(
        self, 
        location: str, 
        bandwidth: str, 
        connection_name: str, 
        lag_id: str, 
        tags: List[Dict[str, str]], 
        provider_name: str, 
        request_mac_sec: bool
    ) -> Connection:
        encryption_mode = EncryptionModeType.NONE

        if request_mac_sec:
            encryption_mode = EncryptionModeType.MUST
        connection = Connection(
            aws_device_v2="mock_device_v2",
            aws_device="mock_device",
            aws_logical_device_id="mock_logical_device_id",
            bandwidth=bandwidth,
            connection_name=connection_name,
            connection_state=ConnectionStateType.AVAILABLE,
            encryption_mode=encryption_mode,
            has_logical_redundancy=False,
            jumbo_frame_capable=False,
            lag_id=lag_id,
            loa_issue_time=datetime.now(),
            location=location,
            mac_sec_capable=request_mac_sec,
            mac_sec_keys=[],
            owner_account=self.account_id,
            partner_name="mock_partner",
            port_encryption_status=PortEncryptionStatusType.DOWN,
            provider_name=provider_name,
            region=self.region_name,
            tags=tags,
            vlan=0,
        )
        self.connections[connection.connection_id] = connection
        return connection
        
    def delete_connection(self, connection_id):
        # implement here
        return owner_account, connection_id, connection_name, connection_state, region, location, bandwidth, vlan, partner_name, loa_issue_time, lag_id, aws_device, jumbo_frame_capable, aws_device_v2, aws_logical_device_id, has_logical_redundancy, tags, provider_name, mac_sec_capable, port_encryption_status, encryption_mode, mac_sec_keys
    
    def update_connection(self, connection_id, connection_name, encryption_mode):
        # implement here
        return owner_account, connection_id, connection_name, connection_state, region, location, bandwidth, vlan, partner_name, loa_issue_time, lag_id, aws_device, jumbo_frame_capable, aws_device_v2, aws_logical_device_id, has_logical_redundancy, tags, provider_name, mac_sec_capable, port_encryption_status, encryption_mode, mac_sec_keys
    

directconnect_backends = BackendDict(DirectConnectBackend, "directconnect")
