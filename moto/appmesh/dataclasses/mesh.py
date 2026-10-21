from dataclasses import dataclass, field
from typing import Any, Literal

from moto.appmesh.dataclasses.shared import Metadata, Status
from moto.appmesh.dataclasses.virtual_gateway import VirtualGateway
from moto.appmesh.dataclasses.virtual_node import VirtualNode
from moto.appmesh.dataclasses.virtual_router import VirtualRouter
from moto.core.utils import unix_time


@dataclass
class MeshSpec:
    egress_filter: dict[Literal["type"], str | None]
    service_discovery: dict[Literal["ip_preference"], str | None]


@dataclass
class Mesh:
    mesh_name: str
    metadata: Metadata
    spec: MeshSpec
    status: Status
    virtual_gateways: dict[str, VirtualGateway] = field(default_factory=dict)
    virtual_nodes: dict[str, VirtualNode] = field(default_factory=dict)
    virtual_routers: dict[str, VirtualRouter] = field(default_factory=dict)
    tags: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:  # type ignore[misc]
        return {
            "meshName": self.mesh_name,
            "metadata": {
                "arn": self.metadata.arn,
                "createdAt": unix_time(self.metadata.created_at),
                "lastUpdatedAt": unix_time(self.metadata.last_updated_at),
                "meshOwner": self.metadata.mesh_owner,
                "resourceOwner": self.metadata.resource_owner,
                "uid": self.metadata.uid,
                "version": self.metadata.version,
            },
            "spec": {
                "egressFilter": self.spec.egress_filter,
                "serviceDiscovery": {
                    "ipPreference": self.spec.service_discovery.get("ip_preference")
                },
            },
            "status": self.status,
        }
