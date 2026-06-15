from dataclasses import dataclass, field
from typing import Any

from moto.appmesh.dataclasses.gateway_route import GatewayRoute
from moto.appmesh.dataclasses.shared import Metadata, MissingField, Status
from moto.appmesh.dataclasses.virtual_node import (
    BackendDefaults,
    ConnectionPool,
    HealthCheck,
    ListenerTLS,
    Logging,
    PortMapping,
)
from moto.appmesh.utils.common import clean_dict


@dataclass
class VirtualGatewayListener:
    connection_pool: ConnectionPool | None
    health_check: HealthCheck | None
    port_mapping: PortMapping
    tls: ListenerTLS | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "connectionPool": (self.connection_pool or MissingField()).to_dict(),
                "healthCheck": (self.health_check or MissingField()).to_dict(),
                "portMapping": self.port_mapping.to_dict(),
                "tls": (self.tls or MissingField()).to_dict(),
            }
        )


@dataclass
class VirtualGatewaySpec:
    backend_defaults: BackendDefaults | None
    listeners: list[VirtualGatewayListener] | None
    logging: Logging | None

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "backendDefaults": (self.backend_defaults or MissingField()).to_dict(),
                "listeners": [listener.to_dict() for listener in self.listeners or []],
                "logging": (self.logging or MissingField()).to_dict(),
            }
        )


@dataclass
class VirtualGatewayMetadata(Metadata):
    mesh_name: str = field(default="")
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
class VirtualGateway:
    mesh_name: str
    mesh_owner: str
    metadata: VirtualGatewayMetadata
    spec: VirtualGatewaySpec
    virtual_gateway_name: str
    gateway_routes: dict[str, GatewayRoute] = field(default_factory=dict)
    status: Status = field(default_factory=lambda: {"status": "ACTIVE"})
    tags: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:  # type: ignore[misc]
        return clean_dict(
            {
                "meshName": self.mesh_name,
                "metadata": self.metadata.formatted_for_crud_apis(),
                "spec": self.spec.to_dict(),
                "status": self.status,
                "virtualGatewayName": self.virtual_gateway_name,
            }
        )
