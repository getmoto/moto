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
        return ActionResult(
            {"connections": [connection.to_dict() for connection in connections]}
        )

    def create_connection(self) -> ActionResult:
        connection: Connection = self.directconnect_backend.create_connection(
            location=self._get_param("location"),
            bandwidth=self._get_param("bandwidth"),
            connection_name=self._get_param("connectionName"),
            lag_id=self._get_param("lagId"),
            tags=self._get_param("tags"),
            provider_name=self._get_param("providerName"),
            request_mac_sec=self._get_param("requestMACSec"),
        )
        return ActionResult(connection.to_dict())

    def delete_connection(self) -> ActionResult:
        connection: Connection = self.directconnect_backend.delete_connection(
            connection_id=self._get_param("connectionId"),
        )
        return ActionResult(connection.to_dict())

    def update_connection(self) -> ActionResult:
        connection: Connection = self.directconnect_backend.update_connection(
            connection_id=self._get_param("connectionId"),
            new_connection_name=self._get_param("connectionName"),
            new_encryption_mode=self._get_param("encryptionMode"),
        )
        return ActionResult(connection.to_dict())

    def associate_mac_sec_key(self) -> ActionResult:
        connection_id = self._get_param("connectionId")
        secret_arn = self._get_param("secretARN")
        ckn = self._get_param("ckn")
        cak = self._get_param("cak")
        connection_id, mac_sec_keys = self.directconnect_backend.associate_mac_sec_key(
            connection_id=connection_id,
            secret_arn=secret_arn,
            ckn=ckn,
            cak=cak,
        )
        return ActionResult(
            {
                "connectionId": connection_id,
                "macSecKeys": [mac_sec_key.to_dict() for mac_sec_key in mac_sec_keys],
            }
        )

    def create_lag(self) -> ActionResult:
        number_of_connections = self._get_param("numberOfConnections")
        location = self._get_param("location")
        connections_bandwidth = self._get_param("connectionsBandwidth")
        lag_name = self._get_param("lagName")
        connection_id = self._get_param("connectionId")
        tags = self._get_param("tags")
        child_connection_tags = self._get_param("childConnectionTags")
        provider_name = self._get_param("providerName")
        request_mac_sec = self._get_param("requestMACSec")
        lag: LAG = self.directconnect_backend.create_lag(
            number_of_connections=number_of_connections,
            location=location,
            connections_bandwidth=connections_bandwidth,
            lag_name=lag_name,
            connection_id=connection_id,
            tags=tags,
            child_connection_tags=child_connection_tags,
            provider_name=provider_name,
            request_mac_sec=request_mac_sec,
        )
        return ActionResult(lag.to_dict())

    def describe_lags(self) -> ActionResult:
        lags = self.directconnect_backend.describe_lags(
            lag_id=self._get_param("lagId"),
        )
        return ActionResult({"lags": [lag.to_dict() for lag in lags]})

    def disassociate_mac_sec_key(self) -> ActionResult:
        connection_id = self._get_param("connectionId")
        secret_arn = self._get_param("secretARN")
        connection_id, mac_sec_key = (
            self.directconnect_backend.disassociate_mac_sec_key(
                connection_id=connection_id,
                secret_arn=secret_arn,
            )
        )
        return ActionResult(
            {
                "connectionId": connection_id,
                "macSecKeys": [mac_sec_key.to_dict()],
            }
        )

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
