from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

Status = Dict[Literal["status"], str]


@dataclass
class MeshSpec:
    egress_filter: Dict[Literal["type"], Optional[str]]
    service_discovery: Dict[Literal["ip_preference"], Optional[str]]


@dataclass
class Metadata:
    arn: str
    mesh_owner: str
    resource_owner: str
    created_at: datetime = datetime.now()
    last_updated_at: datetime = datetime.now()
    uid: str = uuid4().hex
    version: int = 1


@dataclass
class PortMapping:
    port: Optional[int]
    protocol: Optional[str]


@dataclass
class VirtualRouterSpec:
    listeners: List[Dict[Literal["port_mapping"], PortMapping]]


@dataclass
class VirtualRouter:
    mesh_name: str
    metadata: Metadata
    spec: VirtualRouterSpec
    status: Status
    virtual_router_name: str
    tags: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:  # type ignore[misc]
        return {
            "meshName": self.mesh_name,
            "metadata": {
                "arn": self.metadata.arn,
                "createdAt": self.metadata.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
                "lastUpdatedAt": self.metadata.last_updated_at.strftime(
                    "%d/%m/%Y, %H:%M:%S"
                ),
                "meshOwner": self.metadata.mesh_owner,
                "resourceOwner": self.metadata.resource_owner,
                "uid": self.metadata.uid,
                "version": self.metadata.version,
            },
            "spec": {
                "listeners": [
                    {
                        "portMapping": {
                            "port": listener["port_mapping"].port,
                            "protocol": listener["port_mapping"].protocol,
                        }
                    }
                    for listener in self.spec.listeners
                ]
            },
            "status": self.status,
            "virtualRouterName": self.virtual_router_name,
        }


@dataclass
class Mesh:
    mesh_name: str
    metadata: Metadata
    spec: MeshSpec
    status: Status
    tags: List[Dict[str, str]]
    virtual_routers: Dict[str, VirtualRouter] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:  # type ignore[misc]
        return {
            "meshName": self.mesh_name,
            "metadata": {
                "arn": self.metadata.arn,
                "createdAt": self.metadata.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
                "lastUpdatedAt": self.metadata.last_updated_at.strftime(
                    "%d/%m/%Y, %H:%M:%S"
                ),
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
