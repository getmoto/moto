"""AppMeshBackend class with methods for supported APIs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from uuid import uuid4

from moto.appmesh.exceptions import MeshNotFoundError
from moto.core.base_backend import BackendDict, BaseBackend

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
class Spec:
   egress_filter: Dict[Literal["type"], str]
   service_discovery: Dict[Literal["ip_preference"], str]


@dataclass
class Mesh:
    mesh_name: str
    metadata: Metadata
    spec: Spec
    status: Dict[Literal["status"], str]
    tags: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:  # type ignore[misc]
        return {
            "meshName": self.mesh_name,
            "metadata": {
                "arn": self.metadata.arn,
                "createdAt": self.metadata.created_at,
                "lastUpdatedAt": self.metadata.last_updated_at,
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


PAGINATION_MODEL = {
    "list_meshes": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "unique_attribute": "meshName",
    },
    "list_tags_for_resource": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 100,
        "unique_attribute": "key",
    },
}


class AppMeshBackend(BaseBackend):
    """Implementation of AppMesh APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.meshes: Dict[str, Mesh] = dict()

    def create_mesh(
        self,
        client_token: Optional[str],
        mesh_name: str,
        egress_filter: Dict[Literal["type"], str], 
        service_discovery: Dict[Literal["ipPreference"], str],
        tags: List[Dict[str, str]],
    ) -> Mesh:
        from moto.sts import sts_backends

        sts_backend = sts_backends[self.account_id][self.region_name]
        user_id, _, _ = sts_backend.get_caller_identity(
            self.account_id, region=self.region_name
        )
        print("USER ID")
        print(user_id)

        metadata = Metadata(
            arn=f"arn:aws:appmesh:{self.region_name}:{self.account_id}:{mesh_name}",
            mesh_owner=user_id,
            resource_owner=user_id
        )
        spec = Spec(
            egress_filter=egress_filter,
            service_discovery={
                "ip_preference": service_discovery["ipPreference"]
            }
        )
        mesh = Mesh(
            mesh_name=mesh_name,
            spec=spec,
            status={"status": "ACTIVE"},
            metadata=metadata,
            tags=tags,
        )
        self.meshes[mesh_name] = mesh
        return mesh

    def update_mesh(
        self,
        client_token: Optional[str],
        mesh_name: str,
        egress_filter: Optional[Dict[Literal["type"], str]],
        service_discovery: Optional[Dict[Literal["ipPreference"], str]],
    ) -> Mesh:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name)
        updated = False
        if egress_filter is not None:
            self.meshes[mesh_name].spec.egress_filter = egress_filter
            updated = True

        new_ip_preference = (service_discovery or {}).get(
            "ipPreference"
        )
        if new_ip_preference is not None:
            self.meshes[mesh_name].spec.service_discovery["ip_preference"] = new_ip_preference
            updated = True

        if updated:
            self.meshes[mesh_name].metadata.last_updated_at = datetime.now()
            self.meshes[mesh_name].metadata.version += 1
        return self.meshes[mesh_name]

    def describe_mesh(self, mesh_name: str, mesh_owner: Optional[str]) -> Mesh:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name)
        return self.meshes[mesh_name]

    def delete_mesh(self, mesh_name: str) -> Mesh:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name)
        self.meshes[mesh_name].status["status"] = "DELETED"
        mesh = self.meshes[mesh_name].copy()
        del self.meshes[mesh_name]
        return mesh

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_meshes(self, limit: Optional[int], next_token: Optional[str]):
        return [
            {
                "arn": mesh.metadata.arn,
                "createdAt": mesh.metadata.created_at,
                "lastUpdatedAt": mesh.metadata.last_updated_at,
                "meshName": mesh.mesh_name,
                "meshOwner": mesh.metadata.mesh_owner,
                "resourceOwner": mesh.metadata.resource_owner,
                "version": mesh.metadata.version,
            }
            for mesh in self.meshes.values()
        ]

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_tags_for_resource(
        self, limit: int, next_token: str, resource_arn: str
    ) -> Tuple[str, List[Dict[str, str]]]:
        tags = [] # TODO
        return tags

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        # implement here
        return

appmesh_backends = BackendDict(AppMeshBackend, "appmesh")
