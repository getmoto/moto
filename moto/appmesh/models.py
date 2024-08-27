"""AppMeshBackend class with methods for supported APIs."""

from typing import Any, Dict, List, Literal, Optional

from moto.appmesh.dataclasses.mesh import (
    Mesh,
    MeshSpec,
)
from moto.appmesh.dataclasses.route import Route, RouteMetadata, RouteSpec
from moto.appmesh.dataclasses.shared import Metadata
from moto.appmesh.dataclasses.virtual_router import (
    PortMapping,
    VirtualRouter,
    VirtualRouterSpec,
)
from moto.appmesh.exceptions import (
    MeshNotFoundError,
    ResourceNotFoundError,
)
from moto.appmesh.utils import (
    check_route_availability,
    check_route_validity,
    check_router_availability,
    check_router_validity,
    validate_mesh,
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
    "list_routes": {
        "input_token": "next_token",
        "limit_key": "limit",
        "limit_default": 100,
        "unique_attribute": ["routeName"],
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
            raise MeshNotFoundError(mesh_name=mesh_name)
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
            self.meshes[mesh_name].metadata.update_timestamp()
            self.meshes[mesh_name].metadata.version += 1
        return self.meshes[mesh_name]

    def describe_mesh(self, mesh_name: str, mesh_owner: Optional[str]) -> Mesh:
        validate_mesh(meshes=self.meshes, mesh_name=mesh_name, mesh_owner=mesh_owner)
        return self.meshes[mesh_name]

    def delete_mesh(self, mesh_name: str) -> Mesh:
        if mesh_name not in self.meshes:
            raise MeshNotFoundError(mesh_name=mesh_name)
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
        self, mesh_name: str, mesh_owner: Optional[str], virtual_router_name: str
    ) -> VirtualRouter:
        check_router_validity(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
        )
        return self.meshes[mesh_name].virtual_routers[virtual_router_name]

    def create_virtual_router(
        self,
        client_token: str,
        mesh_name: str,
        mesh_owner: Optional[str],
        port_mappings: List[PortMapping],
        tags: List[Dict[str, str]],
        virtual_router_name: str,
    ) -> VirtualRouter:
        check_router_availability(
            meshes=self.meshes,
            mesh_name=mesh_name,
            virtual_router_name=virtual_router_name,
            mesh_owner=mesh_owner,
        )
        owner = mesh_owner or self.meshes[mesh_name].metadata.mesh_owner
        metadata = Metadata(
            mesh_owner=owner,
            resource_owner=owner,
            arn=f"arn:aws:appmesh:{self.region_name}:{self.account_id}:mesh/{mesh_name}/virtualRouter/{virtual_router_name}",
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
        mesh_owner: Optional[str],
        port_mappings: List[PortMapping],
        virtual_router_name: str,
    ) -> VirtualRouter:
        check_router_validity(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
        )
        listeners: List[Dict[Literal["port_mapping"], PortMapping]] = [
            {"port_mapping": port_mapping} for port_mapping in port_mappings
        ]
        spec = VirtualRouterSpec(listeners=listeners)
        virtual_router = self.meshes[mesh_name].virtual_routers[virtual_router_name]
        virtual_router.spec = spec
        virtual_router.metadata.update_timestamp()
        virtual_router.metadata.version += 1
        return virtual_router

    def delete_virtual_router(
        self, mesh_name: str, mesh_owner: Optional[str], virtual_router_name: str
    ) -> VirtualRouter:
        check_router_validity(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
        )
        mesh = self.meshes[mesh_name]
        mesh.virtual_routers[virtual_router_name].status["status"] = "DELETED"
        virtual_router = mesh.virtual_routers[virtual_router_name]
        del mesh.virtual_routers[virtual_router_name]
        return virtual_router

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_virtual_routers(
        self, limit: int, mesh_name: str, mesh_owner: Optional[str], next_token: str
    ):
        validate_mesh(meshes=self.meshes, mesh_name=mesh_name, mesh_owner=mesh_owner)
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
            for virtual_router in self.meshes[mesh_name].virtual_routers.values()
        ]

    def create_route(
        self,
        client_token: Optional[str],
        mesh_name: str,
        mesh_owner: Optional[str],
        route_name: str,
        spec: RouteSpec,
        tags: Optional[List[Dict[str, str]]],
        virtual_router_name: str,
    ) -> Route:
        check_route_availability(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            route_name=route_name,
            virtual_router_name=virtual_router_name,
        )
        owner = mesh_owner or self.meshes[mesh_name].metadata.mesh_owner
        metadata = RouteMetadata(
            arn=f"arn:aws:appmesh:{self.region_name}:{self.account_id}:mesh/{mesh_name}/virtualRouter/{virtual_router_name}/route/{route_name}",
            mesh_name=mesh_name,
            mesh_owner=owner,
            resource_owner=owner,
            route_name=route_name,
            virtual_router_name=virtual_router_name,
        )
        route = Route(
            mesh_name=mesh_name,
            mesh_owner=owner,
            metadata=metadata,
            route_name=route_name,
            spec=spec,
            tags=tags,
            virtual_router_name=virtual_router_name,
        )
        self.meshes[mesh_name].virtual_routers[virtual_router_name].routes[
            route_name
        ] = route
        return route

    def describe_route(
        self,
        mesh_name: str,
        mesh_owner: Optional[str],
        route_name: str,
        virtual_router_name: str,
    ) -> Route:
        check_route_validity(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
            route_name=route_name,
        )
        return (
            self.meshes[mesh_name]
            .virtual_routers[virtual_router_name]
            .routes[route_name]
        )

    def update_route(
        self,
        client_token: Optional[str],
        mesh_name: str,
        mesh_owner: Optional[str],
        route_name: str,
        spec: RouteSpec,
        virtual_router_name: str,
    ) -> Route:
        check_route_validity(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
            route_name=route_name,
        )
        route = (
            self.meshes[mesh_name]
            .virtual_routers[virtual_router_name]
            .routes[route_name]
        )
        route.spec = spec
        route.metadata.version += 1
        route.metadata.update_timestamp()
        return route

    def delete_route(
        self,
        mesh_name: str,
        mesh_owner: Optional[str],
        route_name: str,
        virtual_router_name: str,
    ) -> Route:
        check_route_validity(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
            route_name=route_name,
        )
        route = (
            self.meshes[mesh_name]
            .virtual_routers[virtual_router_name]
            .routes[route_name]
        )
        route.status["status"] = "DELETED"
        del (
            self.meshes[mesh_name]
            .virtual_routers[virtual_router_name]
            .routes[route_name]
        )
        return route

    @paginate(pagination_model=PAGINATION_MODEL)  # type: ignore
    def list_routes(
        self,
        limit: Optional[int],
        mesh_name: str,
        mesh_owner: Optional[str],
        next_token: Optional[str],
        virtual_router_name: str,
    ) -> List[Dict[str, Any]]:
        check_router_validity(
            meshes=self.meshes,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
        )
        virtual_router = self.meshes[mesh_name].virtual_routers[virtual_router_name]
        return [
            route.metadata.formatted_for_list_api()
            for route in virtual_router.routes.values()
        ]


appmesh_backends = BackendDict(AppMeshBackend, "appmesh")
