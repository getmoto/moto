from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from moto.appmesh.dataclasses.shared import Metadata, Status
from moto.appmesh.dataclasses.virtual_router import VirtualRouter


@dataclass
class MeshSpec:
    egress_filter: Dict[Literal["type"], Optional[str]]
    service_discovery: Dict[Literal["ip_preference"], Optional[str]]


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
