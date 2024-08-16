"""AppMeshBackend class with methods for supported APIs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from moto.core.base_backend import BackendDict, BaseBackend


@dataclass
class Mesh:
    mesh_name: str
    metadata: Dict[str, Optional[Union[str, int, datetime]]]
    spec: Dict[str, Optional[Dict[str, Optional[str]]]]
    status: Dict[Literal["status"], str]

    def to_dict(self) -> Dict[str, Any]:  # type ignore[misc]
        service_discovery = self.spec.get("service_discovery") or {}

        return {
            "meshName": self.mesh_name,
            "metadata": {
                "arn": self.metadata.get("arn"),
                "createdAt": self.metadata.get("created_at"),
                "lastUpdatedAt": self.metadata.get("last_updated_at"),
                "meshOwner": self.metadata.get("mesh_owner"),
                "resourceOwner": self.metadata.get("resource_owner"),
                "uid": self.metadata.get("uid"),
                "version": self.metadata.get("version"),
            },
            "spec": {
                "egressFilter": self.spec.get("egress_filter"),
                "serviceDiscovery": {
                    "ipPreference": service_discovery.get("ip_preference")
                },
            },
            "status": self.status,
        }


class AppMeshBackend(BaseBackend):
    """Implementation of AppMesh APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)

    # add methods from here

    def create_mesh(
        self,
        client_token: str,
        mesh_name: str,
        spec: Dict[str, Dict[str, str]],
        tags: List[Dict[str, str]],
    ) -> Mesh:
        # implement here
        return mesh

    def update_mesh(
        self, client_token: str, mesh_name: str, spec: Dict[str, Dict[str, str]]
    ) -> Mesh:
        # implement here
        return mesh

    def describe_mesh(self, mesh_name: str, mesh_owner: str) -> Mesh:
        # implement here
        return mesh

    def delete_mesh(self, mesh_name: str) -> Mesh:
        # implement here
        return mesh

    def list_tags_for_resource(
        self, limit: int, next_token: str, resource_arn: str
    ) -> Tuple[str, List[Dict[str, str]]]:
        # implement here
        return next_token, tags

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]):
        # implement here
        return


appmesh_backends = BackendDict(AppMeshBackend, "appmesh")
