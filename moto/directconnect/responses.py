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
    
    def create_connection(self):
        params = self._get_params()
        location = params.get("location")
        bandwidth = params.get("bandwidth")
        connection_name = params.get("connectionName")
        lag_id = params.get("lagId")
        tags = params.get("tags")
        provider_name = params.get("providerName")
        request_mac_sec = params.get("requestMACSec")
        owner_account, connection_id, connection_name, connection_state, region, location, bandwidth, vlan, partner_name, loa_issue_time, lag_id, aws_device, jumbo_frame_capable, aws_device_v2, aws_logical_device_id, has_logical_redundancy, tags, provider_name, mac_sec_capable, port_encryption_status, encryption_mode, mac_sec_keys = self.directconnect_backend.create_connection(
            location=location,
            bandwidth=bandwidth,
            connection_name=connection_name,
            lag_id=lag_id,
            tags=tags,
            provider_name=provider_name,
            request_mac_sec=request_mac_sec,
        )
        return json.dumps(dict(ownerAccount=owner_account, connectionId=connection_id, connectionName=connection_name, connectionState=connection_state, region=region, location=location, bandwidth=bandwidth, vlan=vlan, partnerName=partner_name, loaIssueTime=loa_issue_time, lagId=lag_id, awsDevice=aws_device, jumboFrameCapable=jumbo_frame_capable, awsDeviceV2=aws_device_v2, awsLogicalDeviceId=aws_logical_device_id, hasLogicalRedundancy=has_logical_redundancy, tags=tags, providerName=provider_name, macSecCapable=mac_sec_capable, portEncryptionStatus=port_encryption_status, encryptionMode=encryption_mode, macSecKeys=mac_sec_keys))
    
    def delete_connection(self):
        params = self._get_params()
        connection_id = params.get("connectionId")
        owner_account, connection_id, connection_name, connection_state, region, location, bandwidth, vlan, partner_name, loa_issue_time, lag_id, aws_device, jumbo_frame_capable, aws_device_v2, aws_logical_device_id, has_logical_redundancy, tags, provider_name, mac_sec_capable, port_encryption_status, encryption_mode, mac_sec_keys = self.directconnect_backend.delete_connection(
            connection_id=connection_id,
        )
        return json.dumps(dict(ownerAccount=owner_account, connectionId=connection_id, connectionName=connection_name, connectionState=connection_state, region=region, location=location, bandwidth=bandwidth, vlan=vlan, partnerName=partner_name, loaIssueTime=loa_issue_time, lagId=lag_id, awsDevice=aws_device, jumboFrameCapable=jumbo_frame_capable, awsDeviceV2=aws_device_v2, awsLogicalDeviceId=aws_logical_device_id, hasLogicalRedundancy=has_logical_redundancy, tags=tags, providerName=provider_name, macSecCapable=mac_sec_capable, portEncryptionStatus=port_encryption_status, encryptionMode=encryption_mode, macSecKeys=mac_sec_keys))
    
    def update_connection(self):
        params = self._get_params()
        connection_id = params.get("connectionId")
        connection_name = params.get("connectionName")
        encryption_mode = params.get("encryptionMode")
        owner_account, connection_id, connection_name, connection_state, region, location, bandwidth, vlan, partner_name, loa_issue_time, lag_id, aws_device, jumbo_frame_capable, aws_device_v2, aws_logical_device_id, has_logical_redundancy, tags, provider_name, mac_sec_capable, port_encryption_status, encryption_mode, mac_sec_keys = self.directconnect_backend.update_connection(
            connection_id=connection_id,
            connection_name=connection_name,
            encryption_mode=encryption_mode,
        )
        # TODO: adjust response
        return json.dumps(dict(ownerAccount=owner_account, connectionId=connection_id, connectionName=connection_name, connectionState=connection_state, region=region, location=location, bandwidth=bandwidth, vlan=vlan, partnerName=partner_name, loaIssueTime=loa_issue_time, lagId=lag_id, awsDevice=aws_device, jumboFrameCapable=jumbo_frame_capable, awsDeviceV2=aws_device_v2, awsLogicalDeviceId=aws_logical_device_id, hasLogicalRedundancy=has_logical_redundancy, tags=tags, providerName=provider_name, macSecCapable=mac_sec_capable, portEncryptionStatus=port_encryption_status, encryptionMode=encryption_mode, macSecKeys=mac_sec_keys))
