"""DirectConnectBackend class with methods for supported APIs."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel

from .enums import (
    ConnectionStateType,
    EncryptionModeType,
    MacSecKeyStateType,
    PortEncryptionStatusType,
)
from .exceptions import ConnectionIdMissing, ConnectionNotFound


@dataclass
class MacSecKey(BaseModel):
    secret_arn: str
    ckn: str
    state: MacSecKeyStateType
    start_on: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "secretARN": self.secret_arn,
            "ckn": self.ckn,
            "state": self.state,
            "startOn": self.start_on,
        }


@dataclass
class Connection(BaseModel):
    aws_device_v2: str
    aws_device: str
    aws_logical_device_id: str
    bandwidth: str
    connection_name: str
    connection_state: ConnectionStateType
    encryption_mode: EncryptionModeType
    has_logical_redundancy: bool
    jumbo_frame_capable: bool
    lag_id: Optional[str]
    loa_issue_time: str
    location: str
    mac_sec_capable: Optional[bool]
    mac_sec_keys: List[MacSecKey]
    owner_account: str
    partner_name: str
    port_encryption_status: PortEncryptionStatusType
    provider_name: Optional[str]
    region: str
    tags: Optional[List[Dict[str, str]]]
    vlan: int
    connection_id: str = field(default="", init=False)

    def __post_init__(self) -> None:
        if self.connection_id == "":
            self.connection_id = f"dx-moto-{self.connection_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def to_dict(
        self,
    ) -> Dict[str, Any]:
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

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.connections: Dict[str, Connection] = {}

    def describe_connections(self, connection_id: Optional[str]) -> List[Connection]:
        if connection_id and connection_id not in self.connections:
            raise ConnectionNotFound(connection_id, self.region_name)
        if connection_id:
            connection = self.connections.get(connection_id)
            return [] if not connection else [connection]
        return list(self.connections.values())

    def create_connection(
        self,
        location: str,
        bandwidth: str,
        connection_name: str,
        lag_id: Optional[str],
        tags: Optional[List[Dict[str, str]]],
        provider_name: Optional[str],
        request_mac_sec: Optional[bool],
    ) -> Connection:
        encryption_mode = EncryptionModeType.NO
        mac_sec_keys = []
        if request_mac_sec:
            encryption_mode = EncryptionModeType.MUST
            mac_sec_keys = [
                MacSecKey(
                    secret_arn="mock_secret_arn",
                    ckn="mock_ckn",
                    state=MacSecKeyStateType.ASSOCIATED,
                    start_on=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            ]
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
            loa_issue_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            location=location,
            mac_sec_capable=request_mac_sec,
            mac_sec_keys=mac_sec_keys,
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

    def delete_connection(self, connection_id: str) -> Connection:
        if not connection_id:
            raise ConnectionIdMissing()
        connection = self.connections.get(connection_id)
        if connection:
            self.connections[
                connection_id
            ].connection_state = ConnectionStateType.DELETED
            return connection
        raise ConnectionNotFound(connection_id, self.region_name)

    def update_connection(
        self,
        connection_id: str,
        new_connection_name: Optional[str],
        new_encryption_mode: Optional[EncryptionModeType],
    ) -> Connection:
        if not connection_id:
            raise ConnectionIdMissing()
        connection = self.connections.get(connection_id)
        if connection:
            if new_connection_name:
                self.connections[connection_id].connection_name = new_connection_name
            if new_encryption_mode:
                self.connections[connection_id].encryption_mode = new_encryption_mode
            return connection
        raise ConnectionNotFound(connection_id, self.region_name)


directconnect_backends = BackendDict(DirectConnectBackend, "directconnect")
