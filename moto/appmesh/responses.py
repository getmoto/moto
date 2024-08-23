"""Handles incoming appmesh requests, invokes methods, returns responses."""

import json

from moto.appmesh.dataclasses.route import (
    GrcpRouteRetryPolicy,
    GrpcRoute,
    HttpRoute,
    RouteSpec,
    TimeValue,
)
from moto.appmesh.utils import (
    get_action_from_route,
    get_grpc_route_match,
    get_http_match_from_route,
    get_http_retry_policy_from_route,
    get_timeout_from_route,
    port_mappings_from_spec,
)
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
        return json.dumps(virtual_router.to_dict())

    def create_virtual_router(self) -> str:
        params = json.loads(self.body)
        client_token = params.get("clientToken")
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        port_mappings = port_mappings_from_spec(params.get("spec"))
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
        return json.dumps(virtual_router.to_dict())

    def update_virtual_router(self) -> str:
        params = json.loads(self.body)
        client_token = params.get("clientToken")
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        port_mappings = port_mappings_from_spec(params.get("spec"))
        virtual_router_name = self._get_param("virtualRouterName")
        virtual_router = self.appmesh_backend.update_virtual_router(
            client_token=client_token,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            port_mappings=port_mappings,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(virtual_router.to_dict())

    def delete_virtual_router(self) -> str:
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        virtual_router_name = self._get_param("virtualRouterName")
        virtual_router = self.appmesh_backend.delete_virtual_router(
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(virtual_router.to_dict())

    def list_virtual_routers(self) -> str:
        limit = self._get_param("limit")
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        next_token = self._get_param("nextToken")
        virtual_routers, next_token = self.appmesh_backend.list_virtual_routers(
            limit=limit,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            next_token=next_token,
        )
        return json.dumps(dict(nextToken=next_token, virtualRouters=virtual_routers))

    def create_route(self) -> str:
        params = json.loads(self.body)
        client_token = params.get("clientToken")
        mesh_name = self._get_param("meshName")
        mesh_owner = self._get_param("meshOwner")
        route_name = self._get_param("routeName")
        tags = params.get("tags")
        virtual_router_name = self._get_param("virtualRouterName")

        # Spec
        _spec = params.get("spec") or {}

        _grpc_route = _spec.get("grpcRoute")
        # TODO
        _http_route = _spec.get("httpRoute")
        _http2_route = _spec.get("http2Route")
        _tcp_route = _spec.get("tcpRoute")
        grpc_route, http_route, http2_route, tcp_route = None, None, None, None
        if _grpc_route is not None:
            # action
            grpc_action = get_action_from_route(_grpc_route)

            # match
            grpc_route_match = get_grpc_route_match(_grpc_route)

            # retryPolicy
            _retry_policy = _grpc_route.get("retryPolicy")
            grpc_retry_policy = None
            if _retry_policy is not None:
                _per_retry_timeout = _retry_policy.get("perRetryTimeout")
                per_retry_timeout = TimeValue(
                    unit=_per_retry_timeout.get("unit"),
                    value=_per_retry_timeout.get("value"),
                )
                grpc_retry_policy = GrcpRouteRetryPolicy(
                    grpc_retry_events=_retry_policy.get("grpcRetryEvents"),
                    http_retry_events=_retry_policy.get("httpRetryEvents"),
                    max_retries=_retry_policy.get("maxRetries"),
                    per_retry_timeout=per_retry_timeout,
                    tcp_retry_events=_retry_policy.get("tcpRetryEvents"),
                )

            # timeout
            grpc_timeout = get_timeout_from_route(_grpc_route)

            # route
            grpc_route = GrpcRoute(
                action=grpc_action,
                match=grpc_route_match,
                retry_policy=grpc_retry_policy,
                timeout=grpc_timeout,
            )

        if _http_route is not None:
            # action
            http_action = get_action_from_route(_http_route)

            # match
            http_match = get_http_match_from_route(_http_route)

            # retryPolicy
            http_retry_policy = get_http_retry_policy_from_route(_http_route)

            # timeout
            http_timeout = get_timeout_from_route(_http_route)

        http_route = HttpRoute(
            action=http_action,
            match=http_match,
            http_retry_policy=http_retry_policy,
            timeout=http_timeout,
        )

        # TODO http2_route
        # TODO tcp_route

        route_spec = RouteSpec(
            grpc_route=grpc_route,
            http_route=http_route,
            http2_route=http2_route,
            priority=_spec.get("priority"),
            tcp_route=tcp_route,
        )
        route = self.appmesh_backend.create_route(
            client_token=client_token,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            route_name=route_name,
            spec=route_spec,
            tags=tags,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(route.to_dict())

    def describe_route(self) -> str:
        params = self._get_params()
        mesh_name = params.get("meshName")
        mesh_owner = params.get("meshOwner")
        route_name = params.get("routeName")
        virtual_router_name = params.get("virtualRouterName")
        route = self.appmesh_backend.describe_route(
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            route_name=route_name,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(route.to_dict())

    def update_route(self) -> str:
        params = self._get_params()
        client_token = params.get("clientToken")
        mesh_name = params.get("meshName")
        mesh_owner = params.get("meshOwner")
        route_name = params.get("routeName")
        spec = params.get("spec")
        virtual_router_name = params.get("virtualRouterName")
        route = self.appmesh_backend.update_route(
            client_token=client_token,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            route_name=route_name,
            spec=spec,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(route.to_dict())

    def delete_route(self) -> str:
        params = self._get_params()
        mesh_name = params.get("meshName")
        mesh_owner = params.get("meshOwner")
        route_name = params.get("routeName")
        virtual_router_name = params.get("virtualRouterName")
        route = self.appmesh_backend.delete_route(
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            route_name=route_name,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(route.to_dict())

    def list_routes(self) -> str:
        params = self._get_params()
        limit = params.get("limit")
        mesh_name = params.get("meshName")
        mesh_owner = params.get("meshOwner")
        next_token = params.get("nextToken")
        virtual_router_name = params.get("virtualRouterName")
        routes, next_token = self.appmesh_backend.list_routes(
            limit=limit,
            mesh_name=mesh_name,
            mesh_owner=mesh_owner,
            next_token=next_token,
            virtual_router_name=virtual_router_name,
        )
        return json.dumps(dict(nextToken=next_token, routes=routes))
