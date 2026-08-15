from dataclasses import dataclass, field
from typing import Any

from moto.appmesh.dataclasses.route import (
    GrpcMetadatum,
    RouteMatchPath,
    RouteMatchQueryParameter,
)
from moto.appmesh.dataclasses.shared import Metadata, MissingField, Status
from moto.appmesh.utils.common import clean_dict


@dataclass
class GatewayRouteVirtualService:
    virtual_service_name: str

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return {"virtualServiceName": self.virtual_service_name}


@dataclass
class GatewayRouteTarget:
    virtual_service: GatewayRouteVirtualService
    port: int | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "port": self.port,
                "virtualService": self.virtual_service.to_dict(),
            }
        )


@dataclass
class GatewayRouteHostnameRewrite:
    default_target_hostname: str

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return {"defaultTargetHostname": self.default_target_hostname}


@dataclass
class HttpGatewayRoutePathRewrite:
    exact: str

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return {"exact": self.exact}


@dataclass
class HttpGatewayRoutePrefixRewrite:
    default_prefix: str | None
    value: str | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict({"defaultPrefix": self.default_prefix, "value": self.value})


@dataclass
class HttpGatewayRouteRewrite:
    hostname: GatewayRouteHostnameRewrite | None
    path: HttpGatewayRoutePathRewrite | None
    prefix: HttpGatewayRoutePrefixRewrite | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "hostname": (self.hostname or MissingField()).to_dict(),
                "path": (self.path or MissingField()).to_dict(),
                "prefix": (self.prefix or MissingField()).to_dict(),
            }
        )


@dataclass
class GrpcGatewayRouteRewrite:
    hostname: GatewayRouteHostnameRewrite | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict({"hostname": (self.hostname or MissingField()).to_dict()})


@dataclass
class HttpGatewayRouteAction:
    target: GatewayRouteTarget
    rewrite: HttpGatewayRouteRewrite | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "rewrite": (self.rewrite or MissingField()).to_dict(),
                "target": self.target.to_dict(),
            }
        )


@dataclass
class GrpcGatewayRouteAction:
    target: GatewayRouteTarget
    rewrite: GrpcGatewayRouteRewrite | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "rewrite": (self.rewrite or MissingField()).to_dict(),
                "target": self.target.to_dict(),
            }
        )


@dataclass
class GatewayRouteHostnameMatch:
    exact: str | None
    suffix: str | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict({"exact": self.exact, "suffix": self.suffix})


@dataclass
class HttpGatewayRouteMatch:
    headers: list[GrpcMetadatum] | None
    hostname: GatewayRouteHostnameMatch | None
    method: str | None
    path: RouteMatchPath | None
    port: int | None
    prefix: str | None
    query_parameters: list[RouteMatchQueryParameter] | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "headers": [header.to_dict() for header in self.headers or []],
                "hostname": (self.hostname or MissingField()).to_dict(),
                "method": self.method,
                "path": (self.path or MissingField()).to_dict(),
                "port": self.port,
                "prefix": self.prefix,
                "queryParameters": [
                    param.to_dict() for param in self.query_parameters or []
                ],
            }
        )


@dataclass
class GrpcGatewayRouteMatch:
    hostname: GatewayRouteHostnameMatch | None
    metadata: list[GrpcMetadatum] | None
    port: int | None
    service_name: str | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "hostname": (self.hostname or MissingField()).to_dict(),
                "metadata": [meta.to_dict() for meta in self.metadata or []],
                "port": self.port,
                "serviceName": self.service_name,
            }
        )


@dataclass
class HttpGatewayRoute:
    action: HttpGatewayRouteAction
    match: HttpGatewayRouteMatch

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {"action": self.action.to_dict(), "match": self.match.to_dict()}
        )


@dataclass
class GrpcGatewayRoute:
    action: GrpcGatewayRouteAction
    match: GrpcGatewayRouteMatch

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {"action": self.action.to_dict(), "match": self.match.to_dict()}
        )


@dataclass
class GatewayRouteSpec:
    priority: int | None
    grpc_route: GrpcGatewayRoute | None = field(default=None)
    http_route: HttpGatewayRoute | None = field(default=None)
    http2_route: HttpGatewayRoute | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "grpcRoute": (self.grpc_route or MissingField()).to_dict(),
                "httpRoute": (self.http_route or MissingField()).to_dict(),
                "http2Route": (self.http2_route or MissingField()).to_dict(),
                "priority": self.priority,
            }
        )


@dataclass
class GatewayRouteMetadata(Metadata):
    mesh_name: str = field(default="")
    gateway_route_name: str = field(default="")
    virtual_gateway_name: str = field(default="")

    def __post_init__(self) -> None:
        if self.mesh_name == "":
            raise TypeError("__init__ missing 1 required argument: 'mesh_name'")
        if self.mesh_owner == "":
            raise TypeError("__init__ missing 1 required argument: 'mesh_owner'")
        if self.virtual_gateway_name == "":
            raise TypeError(
                "__init__ missing 1 required argument: 'virtual_gateway_name'"
            )

    def formatted_for_list_api(self) -> dict[str, Any]:  # type: ignore
        return {
            "arn": self.arn,
            "createdAt": self.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
            "lastUpdatedAt": self.last_updated_at.strftime("%d/%m/%Y, %H:%M:%S"),
            "gatewayRouteName": self.gateway_route_name,
            "meshName": self.mesh_name,
            "meshOwner": self.mesh_owner,
            "resourceOwner": self.resource_owner,
            "version": self.version,
            "virtualGatewayName": self.virtual_gateway_name,
        }

    def formatted_for_crud_apis(self) -> dict[str, Any]:  # type: ignore
        return {
            "arn": self.arn,
            "createdAt": self.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
            "lastUpdatedAt": self.last_updated_at.strftime("%d/%m/%Y, %H:%M:%S"),
            "meshOwner": self.mesh_owner,
            "resourceOwner": self.resource_owner,
            "uid": self.uid,
            "version": self.version,
        }


@dataclass
class GatewayRoute:
    gateway_route_name: str
    mesh_name: str
    mesh_owner: str
    metadata: GatewayRouteMetadata
    spec: GatewayRouteSpec
    virtual_gateway_name: str
    status: Status = field(default_factory=lambda: {"status": "ACTIVE"})
    tags: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "gatewayRouteName": self.gateway_route_name,
                "meshName": self.mesh_name,
                "metadata": self.metadata.formatted_for_crud_apis(),
                "spec": self.spec.to_dict(),
                "status": self.status,
                "virtualGatewayName": self.virtual_gateway_name,
            }
        )
