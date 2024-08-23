"""AppMeshBackend class with methods for supported APIs."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from moto.appmesh.dataclasses.mesh import (
    Mesh,
    MeshSpec,
)
from moto.appmesh.dataclasses.route import Route
from moto.appmesh.dataclasses.shared import Metadata
from moto.appmesh.dataclasses.virtual_router import (
    PortMapping,
    VirtualRouter,
    VirtualRouterSpec,
)
from moto.appmesh.exceptions import (
    MeshNotFoundError,
    MeshOwnerDoesNotMatchError,
    ResourceNotFoundError,
    VirtualRouterNotFoundError,
)
from moto.core.base_backend import BackendDict, BaseBackend
from moto.utilities.paginator import paginate

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
        "unique_attribute": ["key", "value"],
    },
    "list_virtual_routers": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 100,
        "unique_attribute": "virtualRouterName",
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
        egress_filter_type: Optional[str],
        ip_preference: Optional[str],
        tags: List[Dict[str, str]],
    ) -> Mesh:
        from moto.sts import sts_backends

        sts_backend = sts_backends[self.account_id]["global"]
        user_id, _, _ = sts_backend.get_caller_identity(
            self.account_id, region=self.region_name
        )

        metadata = Metadata(
            arn=f"arn:aws:appmesh:{self.region_name}:{self.account_id}:{mesh_name}",
            mesh_owner=user_id,
            resource_owner=user_id,
        )
        spec = MeshSpec(
            egress_filter={"type": egress_filter_type},
            service_discovery={"ip_preference": ip_preference},
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
        egress_filter_type: Optional[str],
        ip_preference: Optional[str],
    ) -> Mesh:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name)
        updated = False
        if egress_filter_type is not None:
            self.meshes[mesh_name].spec.egress_filter["type"] = egress_filter_type
            updated = True

        if ip_preference is not None:
            self.meshes[mesh_name].spec.service_discovery["ip_preference"] = (
                ip_preference
            )
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
        mesh = self.meshes[mesh_name]
        del self.meshes[mesh_name]
        return mesh

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_meshes(self, limit: Optional[int], next_token: Optional[str]):
        return [
            {
                "arn": mesh.metadata.arn,
                "createdAt": mesh.metadata.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
                "lastUpdatedAt": mesh.metadata.last_updated_at.strftime(
                    "%d/%m/%Y, %H:%M:%S"
                ),
                "meshName": mesh.mesh_name,
                "meshOwner": mesh.metadata.mesh_owner,
                "resourceOwner": mesh.metadata.resource_owner,
                "version": mesh.metadata.version,
            }
            for mesh in self.meshes.values()
        ]

    def _get_resource_with_arn(self, resource_arn: str) -> Mesh:
        for mesh in self.meshes.values():
            if mesh.metadata.arn == resource_arn:
                return mesh
        raise ResourceNotFoundError(resource_arn)

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_tags_for_resource(self, limit: int, next_token: str, resource_arn: str):
        return self._get_resource_with_arn(resource_arn=resource_arn).tags

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        if len(tags) > 0:
            mesh = self._get_resource_with_arn(resource_arn=resource_arn)
            mesh.tags.extend(tags)
        return

    def describe_virtual_router(
        self, mesh_name: str, mesh_owner: str, virtual_router_name: str
    ) -> VirtualRouter:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name=mesh_name)
        mesh = self.meshes[mesh_name]
        if mesh.metadata.mesh_owner != mesh_owner:
            raise MeshOwnerDoesNotMatchError(mesh_name, mesh_owner)
        if virtual_router_name not in mesh.virtual_routers:
            raise VirtualRouterNotFoundError(
                virtual_router_name=virtual_router_name, mesh_name=mesh_name
            )
        return mesh.virtual_routers[virtual_router_name]

    def create_virtual_router(
        self,
        client_token: str,
        mesh_name: str,
        mesh_owner: str,
        port_mappings: List[PortMapping],
        tags: List[Dict[str, str]],
        virtual_router_name: str,
    ) -> VirtualRouter:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name=mesh_name)
        mesh = self.meshes[mesh_name]
        if mesh.metadata.mesh_owner != mesh_owner:
            raise MeshOwnerDoesNotMatchError(mesh_name, mesh_owner)
        metadata = Metadata(
            mesh_owner=mesh_owner, resource_owner=mesh_owner, arn="TODO"
        )
        listeners: List[Dict[Literal["port_mapping"], PortMapping]] = [
            {"port_mapping": port_mapping} for port_mapping in port_mappings
        ]
        spec = VirtualRouterSpec(listeners=listeners)
        virtual_router = VirtualRouter(
            virtual_router_name=virtual_router_name,
            mesh_name=mesh_name,
            metadata=metadata,
            status={"status": "ACTIVE"},
            spec=spec,
            tags=tags,
        )
        self.meshes[mesh_name].virtual_routers[virtual_router_name] = virtual_router
        return virtual_router

    def update_virtual_router(
        self,
        client_token: str,
        mesh_name: str,
        mesh_owner: str,
        port_mappings: List[PortMapping],
        virtual_router_name: str,
    ) -> VirtualRouter:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name=mesh_name)
        mesh = self.meshes[mesh_name]
        if mesh.metadata.mesh_owner != mesh_owner:
            raise MeshOwnerDoesNotMatchError(mesh_name, mesh_owner)
        if virtual_router_name not in mesh.virtual_routers:
            raise VirtualRouterNotFoundError(
                virtual_router_name=virtual_router_name, mesh_name=mesh_name
            )
        listeners: List[Dict[Literal["port_mapping"], PortMapping]] = [
            {"port_mapping": port_mapping} for port_mapping in port_mappings
        ]
        spec = VirtualRouterSpec(listeners=listeners)
        virtual_router = mesh.virtual_routers[virtual_router_name]
        virtual_router.spec = spec
        virtual_router.metadata.last_updated_at = datetime.now()
        virtual_router.metadata.version += 1
        return virtual_router

    def delete_virtual_router(
        self, mesh_name: str, mesh_owner: str, virtual_router_name: str
    ) -> VirtualRouter:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name=mesh_name)
        mesh = self.meshes[mesh_name]
        if mesh.metadata.mesh_owner != mesh_owner:
            raise MeshOwnerDoesNotMatchError(mesh_name, mesh_owner)
        if virtual_router_name not in mesh.virtual_routers:
            raise VirtualRouterNotFoundError(
                virtual_router_name=virtual_router_name, mesh_name=mesh_name
            )
        mesh.virtual_routers[virtual_router_name].status["status"] = "DELETED"
        virtual_router = mesh.virtual_routers[virtual_router_name]
        del mesh.virtual_routers[virtual_router_name]
        return virtual_router

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_virtual_routers(
        self, limit: int, mesh_name: str, mesh_owner: str, next_token: str
    ):
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name=mesh_name)
        mesh = self.meshes[mesh_name]
        if mesh.metadata.mesh_owner != mesh_owner:
            raise MeshOwnerDoesNotMatchError(mesh_name, mesh_owner)
        return [
            {
                "arn": virtual_router.metadata.arn,
                "createdAt": virtual_router.metadata.created_at.strftime(
                    "%d/%m/%Y, %H:%M:%S"
                ),
                "lastUpdatedAt": virtual_router.metadata.last_updated_at.strftime(
                    "%d/%m/%Y, %H:%M:%S"
                ),
                "meshName": virtual_router.mesh_name,
                "meshOwner": virtual_router.metadata.mesh_owner,
                "resourceOwner": virtual_router.metadata.resource_owner,
                "version": virtual_router.metadata.version,
                "virtualRouterName": virtual_router.virtual_router_name,
            }
            for virtual_router in mesh.virtual_routers.values()
        ]

    def create_route(
        self,
        client_token,
        mesh_name,
        mesh_owner,
        route_name,
        spec,
        tags,
        virtual_router_name,
    ) -> Route:
        # implement here
        return route

    def describe_route(
        self, mesh_name, mesh_owner, route_name, virtual_router_name
    ) -> Route:
        # implement here
        return route

    def update_route(
        self, client_token, mesh_name, mesh_owner, route_name, spec, virtual_router_name
    ) -> Route:
        # implement here
        return route

    def delete_route(
        self, mesh_name, mesh_owner, route_name, virtual_router_name
    ) -> Route:
        # implement here
        return route

    def list_routes(
        self, limit, mesh_name, mesh_owner, next_token, virtual_router_name
    ):
        # implement here
        return next_token, routes


appmesh_backends = BackendDict(AppMeshBackend, "appmesh")
