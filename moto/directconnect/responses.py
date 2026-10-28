"""Handles incoming directconnect requests, invokes methods, returns responses."""

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import LAG, Connection, DirectConnectBackend, directconnect_backends


class DirectConnectResponse(BaseResponse):
    """Handler for DirectConnect requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="directconnect")
        self.automated_parameter_parsing = True

    @property
    def directconnect_backend(self) -> DirectConnectBackend:
        return directconnect_backends[self.current_account][self.region]

    def describe_connections(self) -> ActionResult:
        connections = self.directconnect_backend.describe_connections(
            connection_id=self._get_param("connectionId"),
        )
        result = {
            "connections": [
                {
                    "awsDevice": connection.aws_device,
                    "awsDeviceV2": connection.aws_device_v2,
                    "awsLogicalDeviceId": connection.aws_logical_device_id,
                    "bandwidth": connection.bandwidth,
                    "connectionId": connection.connection_id,
                    "connectionName": connection.connection_name,
                    "connectionState": connection.connection_state,
                    "encryptionMode": connection.encryption_mode,
                    "hasLogicalRedundancy": connection.has_logical_redundancy,
                    "jumboFrameCapable": connection.jumbo_frame_capable,
                    "lagId": connection.lag_id,
                    "loaIssueTime": connection.loa_issue_time,
                    "location": connection.location,
                    "macSecCapable": connection.mac_sec_capable,
                    "macSecKeys": connection.mac_sec_keys,
                    "partnerName": connection.partner_name,
                    "portEncryptionStatus": connection.port_encryption_status,
                    "providerName": connection.provider_name,
                    "region": connection.region,
                    "tags": self.directconnect_backend.list_tags_for_resource(
                        connection.connection_id
                    ),
                    "vlan": connection.vlan,
                }
                for connection in connections
            ]
        }
        return ActionResult(result)

    def create_connection(self) -> ActionResult:
        connection: Connection = self.directconnect_backend.create_connection(
            location=self._get_param("location"),
            bandwidth=self._get_param("bandwidth"),
            connection_name=self._get_param("connectionName"),
            lag_id=self._get_param("lagId"),
            tags=self._get_param("tags"),
            provider_name=self._get_param("providerName"),
            request_mac_sec=self._get_bool_param("requestMACSec"),
        )
        result = {
            "awsDevice": connection.aws_device,
            "awsDeviceV2": connection.aws_device_v2,
            "awsLogicalDeviceId": connection.aws_logical_device_id,
            "bandwidth": connection.bandwidth,
            "connectionId": connection.connection_id,
            "connectionName": connection.connection_name,
            "connectionState": connection.connection_state,
            "encryptionMode": connection.encryption_mode,
            "hasLogicalRedundancy": connection.has_logical_redundancy,
            "jumboFrameCapable": connection.jumbo_frame_capable,
            "lagId": connection.lag_id,
            "loaIssueTime": connection.loa_issue_time,
            "location": connection.location,
            "macSecCapable": connection.mac_sec_capable,
            "macSecKeys": connection.mac_sec_keys,
            "partnerName": connection.partner_name,
            "portEncryptionStatus": connection.port_encryption_status,
            "providerName": connection.provider_name,
            "region": connection.region,
            "tags": self.directconnect_backend.list_tags_for_resource(
                connection.connection_id
            ),
            "vlan": connection.vlan,
        }
        return ActionResult(result)

    def delete_connection(self) -> ActionResult:
        connection: Connection = self.directconnect_backend.delete_connection(
            connection_id=self._get_param("connectionId"),
        )
        result = {
            "awsDevice": connection.aws_device,
            "awsDeviceV2": connection.aws_device_v2,
            "awsLogicalDeviceId": connection.aws_logical_device_id,
            "bandwidth": connection.bandwidth,
            "connectionId": connection.connection_id,
            "connectionName": connection.connection_name,
            "connectionState": connection.connection_state,
            "encryptionMode": connection.encryption_mode,
            "hasLogicalRedundancy": connection.has_logical_redundancy,
            "jumboFrameCapable": connection.jumbo_frame_capable,
            "lagId": connection.lag_id,
            "loaIssueTime": connection.loa_issue_time,
            "location": connection.location,
            "macSecCapable": connection.mac_sec_capable,
            "macSecKeys": connection.mac_sec_keys,
            "partnerName": connection.partner_name,
            "portEncryptionStatus": connection.port_encryption_status,
            "providerName": connection.provider_name,
            "region": connection.region,
            "tags": self.directconnect_backend.list_tags_for_resource(
                connection.connection_id
            ),
            "vlan": connection.vlan,
        }
        return ActionResult(result)

    def update_connection(self) -> ActionResult:
        connection: Connection = self.directconnect_backend.update_connection(
            connection_id=self._get_param("connectionId"),
            new_connection_name=self._get_param("connectionName"),
            new_encryption_mode=self._get_param("encryptionMode"),
        )
        result = {
            "awsDevice": connection.aws_device,
            "awsDeviceV2": connection.aws_device_v2,
            "awsLogicalDeviceId": connection.aws_logical_device_id,
            "bandwidth": connection.bandwidth,
            "connectionId": connection.connection_id,
            "connectionName": connection.connection_name,
            "connectionState": connection.connection_state,
            "encryptionMode": connection.encryption_mode,
            "hasLogicalRedundancy": connection.has_logical_redundancy,
            "jumboFrameCapable": connection.jumbo_frame_capable,
            "lagId": connection.lag_id,
            "loaIssueTime": connection.loa_issue_time,
            "location": connection.location,
            "macSecCapable": connection.mac_sec_capable,
            "macSecKeys": connection.mac_sec_keys,
            "partnerName": connection.partner_name,
            "portEncryptionStatus": connection.port_encryption_status,
            "providerName": connection.provider_name,
            "region": connection.region,
            "tags": self.directconnect_backend.list_tags_for_resource(
                connection.connection_id
            ),
            "vlan": connection.vlan,
        }
        return ActionResult(result)

    def associate_mac_sec_key(self) -> ActionResult:
        connection_id, mac_sec_keys = self.directconnect_backend.associate_mac_sec_key(
            connection_id=self._get_param("connectionId"),
            secret_arn=self._get_param("secretARN"),
            ckn=self._get_param("ckn"),
            cak=self._get_param("cak"),
        )
        result = {
            "connectionId": connection_id,
            "macSecKeys": mac_sec_keys,
        }
        return ActionResult(result)

    def create_lag(self) -> ActionResult:
        lag: LAG = self.directconnect_backend.create_lag(
            number_of_connections=self._get_param("numberOfConnections"),
            location=self._get_param("location"),
            connections_bandwidth=self._get_param("connectionsBandwidth"),
            lag_name=self._get_param("lagName"),
            connection_id=self._get_param("connectionId"),
            tags=self._get_param("tags"),
            child_connection_tags=self._get_param("childConnectionTags"),
            provider_name=self._get_param("providerName"),
            request_mac_sec=self._get_bool_param("requestMACSec"),
        )
        result = {
            "awsDevice": lag.aws_device,
            "awsDeviceV2": lag.aws_device_v2,
            "awsLogicalDeviceId": lag.aws_logical_device_id,
            "connectionsBandwidth": lag.connections_bandwidth,
            "numberOfConnections": lag.number_of_connections,
            "minimumLinks": lag.minimum_links,
            "connections": [
                {
                    "awsDevice": connection.aws_device,
                    "awsDeviceV2": connection.aws_device_v2,
                    "awsLogicalDeviceId": connection.aws_logical_device_id,
                    "bandwidth": connection.bandwidth,
                    "connectionId": connection.connection_id,
                    "connectionName": connection.connection_name,
                    "connectionState": connection.connection_state,
                    "encryptionMode": connection.encryption_mode,
                    "hasLogicalRedundancy": connection.has_logical_redundancy,
                    "jumboFrameCapable": connection.jumbo_frame_capable,
                    "lagId": connection.lag_id,
                    "loaIssueTime": connection.loa_issue_time,
                    "location": connection.location,
                    "macSecCapable": connection.mac_sec_capable,
                    "macSecKeys": connection.mac_sec_keys,
                    "partnerName": connection.partner_name,
                    "portEncryptionStatus": connection.port_encryption_status,
                    "providerName": connection.provider_name,
                    "region": connection.region,
                    "tags": self.directconnect_backend.list_tags_for_resource(
                        connection.connection_id
                    ),
                    "vlan": connection.vlan,
                }
                for connection in lag.connections
            ],
            "lagId": lag.lag_id,
            "lagName": lag.lag_name,
            "lagState": lag.lag_state,
            "encryptionMode": lag.encryption_mode,
            "hasLogicalRedundancy": lag.has_logical_redundancy,
            "jumboFrameCapable": lag.jumbo_frame_capable,
            "location": lag.location,
            "macSecCapable": lag.mac_sec_capable,
            "macSecKeys": lag.mac_sec_keys,
            "providerName": lag.provider_name,
            "region": lag.region,
            "tags": self.directconnect_backend.list_tags_for_resource(lag.lag_id),
        }
        return ActionResult(result)

    def describe_lags(self) -> ActionResult:
        lags = self.directconnect_backend.describe_lags(
            lag_id=self._get_param("lagId"),
        )
        result = {
            "lags": [
                {
                    "awsDevice": lag.aws_device,
                    "awsDeviceV2": lag.aws_device_v2,
                    "awsLogicalDeviceId": lag.aws_logical_device_id,
                    "connectionsBandwidth": lag.connections_bandwidth,
                    "numberOfConnections": lag.number_of_connections,
                    "minimumLinks": lag.minimum_links,
                    "connections": [
                        {
                            "awsDevice": connection.aws_device,
                            "awsDeviceV2": connection.aws_device_v2,
                            "awsLogicalDeviceId": connection.aws_logical_device_id,
                            "bandwidth": connection.bandwidth,
                            "connectionId": connection.connection_id,
                            "connectionName": connection.connection_name,
                            "connectionState": connection.connection_state,
                            "encryptionMode": connection.encryption_mode,
                            "hasLogicalRedundancy": connection.has_logical_redundancy,
                            "jumboFrameCapable": connection.jumbo_frame_capable,
                            "lagId": connection.lag_id,
                            "loaIssueTime": connection.loa_issue_time,
                            "location": connection.location,
                            "macSecCapable": connection.mac_sec_capable,
                            "macSecKeys": connection.mac_sec_keys,
                            "partnerName": connection.partner_name,
                            "portEncryptionStatus": connection.port_encryption_status,
                            "providerName": connection.provider_name,
                            "region": connection.region,
                            "tags": self.directconnect_backend.list_tags_for_resource(
                                connection.connection_id
                            ),
                            "vlan": connection.vlan,
                        }
                        for connection in lag.connections
                    ],
                    "lagId": lag.lag_id,
                    "lagName": lag.lag_name,
                    "lagState": lag.lag_state,
                    "encryptionMode": lag.encryption_mode,
                    "hasLogicalRedundancy": lag.has_logical_redundancy,
                    "jumboFrameCapable": lag.jumbo_frame_capable,
                    "location": lag.location,
                    "macSecCapable": lag.mac_sec_capable,
                    "macSecKeys": lag.mac_sec_keys,
                    "providerName": lag.provider_name,
                    "region": lag.region,
                    "tags": self.directconnect_backend.list_tags_for_resource(
                        lag.lag_id
                    ),
                }
                for lag in lags
            ]
        }
        return ActionResult(result)

    def disassociate_mac_sec_key(self) -> ActionResult:
        connection_id, mac_sec_key = (
            self.directconnect_backend.disassociate_mac_sec_key(
                connection_id=self._get_param("connectionId"),
                secret_arn=self._get_param("secretARN"),
            )
        )
        result = {
            "connectionId": connection_id,
            "macSecKeys": [mac_sec_key],
        }
        return ActionResult(result)

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tags = self._get_param("tags") or []
        tags = {tag["key"]: tag.get("value") for tag in tags}
        self.directconnect_backend.tag_resource(resource_arn, tags)
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys", [])
        self.directconnect_backend.untag_resource(resource_arn, tag_keys)
        return EmptyResult()

    def describe_tags(self) -> ActionResult:
        resource_arns = self._get_param("resourceArns")
        tags = self.directconnect_backend.list_tags_for_resources(
            resource_arns=resource_arns
        )
        return ActionResult(tags)
