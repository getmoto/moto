"""Handles incoming appmesh requests, invokes methods, returns responses."""

import json
from typing import Any, List

from moto.appmesh.dataclasses import PortMapping
from moto.core.responses import BaseResponse

from .models import AppMeshBackend, appmesh_backends


class AppMeshResponse(BaseResponse):
    """Handler for AppMesh requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="appmesh")

    @property
    def appmesh_backend(self) -> AppMeshBackend:
        """Return backend instance specific for this region."""
        return appmesh_backends[self.current_account][self.region]

    def create_mesh(self) -> str:
        params = json.loads(self.body)
        client_token = params.get("clientToken")
        mesh_name = params.get("meshName")
        spec = params.get("spec") or {}
        egress_filter_type = (spec.get("egressFilter") or {}).get("type")
        ip_preference = (spec.get("serviceDiscovery") or {}).get("ipPreference")
        tags = params.get("tags")
        mesh = self.appmesh_backend.create_mesh(
            client_token=client_token,
            mesh_name=mesh_name,
            egress_filter_type=egress_filter_type,
            ip_preference=ip_preference,
            tags=tags,
        )
        return json.dumps(mesh.to_dict())

    def update_mesh(self) -> str:
        params = json.loads(self.body)
        client_token = params.get("clientToken")
        mesh_name = self._get_param("meshName")
        spec = params.get("spec") or {}
        egress_filter_type = (spec.get("egressFilter") or {}).get("type")
        ip_preference = (spec.get("serviceDiscovery") or {}).get("ipPreference")
        mesh = self.appmesh_backend.update_mesh(
            client_token=client_token,
            mesh_name=mesh_name,
            egress_filter_type=egress_filter_type,
            ip_preference=ip_preference,
        )
        return json.dumps(mesh.to_dict())

    def describe_mesh(self) -> str:
        mesh_name = self._get_param(param_name="meshName", if_none="")
        mesh_owner = self._get_param("meshOwner")
        mesh = self.appmesh_backend.describe_mesh(
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
        )
        return json.dumps(mesh.to_dict())

    def delete_mesh(self) -> str:
        mesh_name = self._get_param("meshName")
        mesh = self.appmesh_backend.delete_mesh(
            mesh_name=mesh_name,
        )
        return json.dumps(mesh.to_dict())

    def list_meshes(self) -> str:
        params = self._get_params()
        limit = params.get("limit")
        next_token = params.get("nextToken")
        meshes, next_token = self.appmesh_backend.list_meshes(
            limit=limit,
            next_token=next_token,
        )
        return json.dumps(dict(meshes=meshes, nextToken=next_token))

    def list_tags_for_resource(self) -> str:
        params = self._get_params()
        limit = params.get("limit")
        next_token = params.get("nextToken")
        resource_arn = params.get("resourceArn")
        tags, next_token = self.appmesh_backend.list_tags_for_resource(
            limit=limit,
            next_token=next_token,
            resource_arn=resource_arn,
        )
        return json.dumps(dict(nextToken=next_token, tags=tags))

    def tag_resource(self) -> str:
        params = json.loads(self.body)
        resource_arn = self._get_param("resourceArn")
        tags = params.get("tags")
        self.appmesh_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return json.dumps(dict())

    def describe_virtual_router(self) -> str:
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        virtual_router_name = self._get_param("virtualRouterName")
        virtual_router = self.appmesh_backend.describe_virtual_router(
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(dict(virtualRouter=virtual_router.to_dict()))

    def _port_mappings_from_spec(self, spec: Any) -> List[PortMapping]:
        return [
            PortMapping(
                port=(listener.get("portMapping") or {}).get("port"),
                protocol=(listener.get("portMapping") or {}).get("protocol"),
            )
            for listener in ((spec or {}).get("listeners") or [])
        ]

    def create_virtual_router(self) -> str:
        params = json.loads(self.body)
        client_token = params.get("clientToken")
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        port_mappings = self._port_mappings_from_spec(params.get("spec"))
        tags = params.get("tags")
        virtual_router_name = params.get("virtualRouterName")
        virtual_router = self.appmesh_backend.create_virtual_router(
            client_token=client_token,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            port_mappings=port_mappings,
            tags=tags,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(dict(virtualRouter=virtual_router.to_dict()))

    def update_virtual_router(self) -> str:
        params = json.loads(self.body)
        client_token = params.get("clientToken")
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        port_mappings = self._port_mappings_from_spec(params.get("spec"))
        virtual_router_name = params.get("virtualRouterName")
        virtual_router = self.appmesh_backend.update_virtual_router(
            client_token=client_token,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            port_mappings=port_mappings,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(dict(virtualRouter=virtual_router.to_dict()))

    def delete_virtual_router(self) -> str:
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        virtual_router_name = self._get_param("virtualRouterName")
        virtual_router = self.appmesh_backend.delete_virtual_router(
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(dict(virtualRouter=virtual_router.to_dict()))

    def list_virtual_routers(self) -> str:
        params = self._get_params()
        limit = params.get("limit")
        mesh_name = params.get("meshName")
        mesh_owner = params.get("meshOwner")
        next_token = params.get("nextToken")
        next_token, virtual_routers = self.appmesh_backend.list_virtual_routers(
            limit=limit,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            next_token=next_token,
        )
        return json.dumps(dict(nextToken=next_token, virtualRouters=virtual_routers))
