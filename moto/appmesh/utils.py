from typing import Any, Dict, List, Optional

from moto.appmesh.dataclasses.mesh import Mesh
from moto.appmesh.dataclasses.route import (
    GrcpRouteRetryPolicy,
    GrpcMetadatum,
    GrpcRoute,
    GrpcRouteMatch,
    HttpRoute,
    HttpRouteMatch,
    HttpRouteRetryPolicy,
    Match,
    QueryParameterMatch,
    Range,
    RouteAction,
    RouteActionWeightedTarget,
    RouteMatchPath,
    RouteMatchQueryParameter,
    RouteSpec,
    TCPRoute,
    TCPRouteMatch,
    Timeout,
    TimeValue,
)
from moto.appmesh.dataclasses.virtual_router import PortMapping
from moto.appmesh.exceptions import (
    MeshNotFoundError,
    MeshOwnerDoesNotMatchError,
    RouteNameAlreadyTakenError,
    RouteNotFoundError,
    VirtualRouterNameAlreadyTakenError,
    VirtualRouterNotFoundError,
)


def port_mappings_from_router_spec(spec: Any) -> List[PortMapping]:  # type: ignore[misc]
    return [
        PortMapping(
            port=(listener.get("portMapping") or {}).get("port"),
            protocol=(listener.get("portMapping") or {}).get("protocol"),
        )
        for listener in ((spec or {}).get("listeners") or [])
    ]


def get_action_from_route(route: Any) -> RouteAction:  # type: ignore[misc]
    weighted_targets = [
        RouteActionWeightedTarget(
            port=target.get("port"),
            virtual_node=target.get("virtualNode"),
            weight=target.get("weight"),
        )
        for target in (route.get("action") or {}).get("weightedTargets") or []
    ]
    return RouteAction(weighted_targets=weighted_targets)


def get_route_match_metadata(metadata: List[Any]) -> List[GrpcMetadatum]:  # type: ignore[misc]
    output = []
    for _metadatum in metadata:
        _match = _metadatum.get("match")
        match = None
        if _match is not None:
            _range = _match.get("range")
            range = None
            if _range is not None:
                range = Range(start=_range.get("start"), end=_range.get("end"))
            match = Match(
                exact=_match.get("exact"),
                prefix=_match.get("prefix"),
                range=range,
                regex=_match.get("regex"),
                suffix=_match.get("suffix"),
            )
        output.append(
            GrpcMetadatum(
                invert=_metadatum.get("invert"),
                match=match,
                name=_metadatum.get("name"),
            )
        )
    return output


def get_grpc_route_match(route: Any) -> GrpcRouteMatch:  # type: ignore[misc]
    _route_match = route.get("match")
    metadata = None
    if _route_match is not None:
        metadata = get_route_match_metadata(_route_match.get("metadata") or [])
    return GrpcRouteMatch(
        metadata=metadata,
        method_name=_route_match.get("methodName"),
        port=_route_match.get("port"),
        service_name=_route_match.get("serviceName"),
    )


def get_http_match_from_route(route: Any) -> HttpRouteMatch:  # type: ignore[misc]
    _route_match = route.get("match") or {}
    headers, path, query_parameters = None, None, None
    if _route_match is not None:
        headers = get_route_match_metadata(_route_match.get("headers") or [])
        _path = _route_match.get("path")
        if _path is not None:
            path = RouteMatchPath(exact=_path.get("exact"), regex=_path.get("regex"))
        _query_parameters = _route_match.get("queryParameters")
        if _query_parameters is not None:
            query_parameters = []
            for _param in _query_parameters:
                _match = _param.get("match")
                match = None
                if _match is not None:
                    match = QueryParameterMatch(exact=_match.get("exact"))
                query_parameters.append(
                    RouteMatchQueryParameter(name=_param.get("name"), match=match)
                )
    return HttpRouteMatch(
        headers=headers,
        method=(_route_match or {}).get("method"),
        path=path,
        port=(_route_match or {}).get("port"),
        prefix=(_route_match or {}).get("prefix"),
        query_parameters=query_parameters,
        scheme=(_route_match or {}).get("scheme"),
    )


def get_http_retry_policy_from_route(route: Any) -> Optional[HttpRouteRetryPolicy]:  # type: ignore[misc]
    _retry_policy = route.get("retryPolicy")
    retry_policy = None
    if _retry_policy is not None:
        _per_retry_timeout = _retry_policy.get("perRetryTimeout")
        per_retry_timeout = TimeValue(
            unit=_per_retry_timeout.get("unit"), value=_per_retry_timeout.get("value")
        )
        retry_policy = HttpRouteRetryPolicy(
            max_retries=_retry_policy.get("maxRetries"),
            http_retry_events=_retry_policy.get("httpRetryEvents"),
            per_retry_timeout=per_retry_timeout,
            tcp_retry_events=_retry_policy.get("tcpRetryEvents"),
        )
    return retry_policy


def get_timeout_from_route(route: Any) -> Optional[Timeout]:  # type: ignore[misc]
    _timeout = route.get("timeout") or {}
    idle, per_request = None, None
    _idle = _timeout.get("idle")
    if _idle is not None:
        idle = TimeValue(unit=_idle.get("unit"), value=_idle.get("value"))
    _per_request = _timeout.get("perRequest")
    if _per_request is not None:
        per_request = TimeValue(
            unit=_per_request.get("unit"), value=_per_request.get("value")
        )
    return (
        Timeout(idle=idle, per_request=per_request)
        if idle is not None or per_request is not None
        else None
    )


def validate_mesh(
    meshes: Dict[str, Mesh], mesh_name: str, mesh_owner: Optional[str]
) -> None:
    if mesh_name not in meshes:
        raise MeshNotFoundError(mesh_name=mesh_name)
    if mesh_owner is not None and meshes[mesh_name].metadata.mesh_owner != mesh_owner:
        raise MeshOwnerDoesNotMatchError(mesh_name, mesh_owner)


def check_router_availability(
    meshes: Dict[str, Mesh],
    mesh_name: str,
    mesh_owner: Optional[str],
    virtual_router_name: str,
) -> None:
    validate_mesh(meshes=meshes, mesh_name=mesh_name, mesh_owner=mesh_owner)
    if virtual_router_name in meshes[mesh_name].virtual_routers:
        raise VirtualRouterNameAlreadyTakenError(
            virtual_router_name=virtual_router_name, mesh_name=mesh_name
        )
    return


def check_router_validity(
    meshes: Dict[str, Mesh],
    mesh_name: str,
    mesh_owner: Optional[str],
    virtual_router_name: str,
) -> None:
    validate_mesh(meshes=meshes, mesh_name=mesh_name, mesh_owner=mesh_owner)
    if virtual_router_name not in meshes[mesh_name].virtual_routers:
        raise VirtualRouterNotFoundError(
            virtual_router_name=virtual_router_name, mesh_name=mesh_name
        )
    return


def check_route_validity(
    meshes: Dict[str, Mesh],
    mesh_name: str,
    mesh_owner: Optional[str],
    virtual_router_name: str,
    route_name: str,
) -> None:
    check_router_validity(
        meshes=meshes,
        mesh_name=mesh_name,
        mesh_owner=mesh_owner,
        virtual_router_name=virtual_router_name,
    )
    if route_name not in meshes[mesh_name].virtual_routers[virtual_router_name].routes:
        raise RouteNotFoundError(
            mesh_name=mesh_name,
            virtual_router_name=virtual_router_name,
            route_name=route_name,
        )
    return


def check_route_availability(
    meshes: Dict[str, Mesh],
    mesh_name: str,
    mesh_owner: Optional[str],
    virtual_router_name: str,
    route_name: str,
) -> None:
    check_router_validity(
        meshes=meshes,
        mesh_name=mesh_name,
        mesh_owner=mesh_owner,
        virtual_router_name=virtual_router_name,
    )
    if route_name in meshes[mesh_name].virtual_routers[virtual_router_name].routes:
        raise RouteNameAlreadyTakenError(
            mesh_name=mesh_name,
            virtual_router_name=virtual_router_name,
            route_name=route_name,
        )
    return


def build_spec(spec: Dict[str, Any]) -> RouteSpec:  # type: ignore[misc]
    _grpc_route = spec.get("grpcRoute")
    _http_route = spec.get("httpRoute")
    _http2_route = spec.get("http2Route")
    _tcp_route = spec.get("tcpRoute")
    grpc_route, http_route, http2_route, tcp_route = None, None, None, None
    if _grpc_route is not None:
        grpc_action = get_action_from_route(_grpc_route)
        grpc_route_match = get_grpc_route_match(_grpc_route)

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

        grpc_timeout = get_timeout_from_route(_grpc_route)

        grpc_route = GrpcRoute(
            action=grpc_action,
            match=grpc_route_match,
            retry_policy=grpc_retry_policy,
            timeout=grpc_timeout,
        )

    if _http_route is not None:
        http_action = get_action_from_route(_http_route)
        http_match = get_http_match_from_route(_http_route)
        http_retry_policy = get_http_retry_policy_from_route(_http_route)
        http_timeout = get_timeout_from_route(_http_route)

        http_route = HttpRoute(
            action=http_action,
            match=http_match,
            retry_policy=http_retry_policy,
            timeout=http_timeout,
        )

    if _http2_route is not None:
        http2_action = get_action_from_route(_http2_route)
        http2_match = get_http_match_from_route(_http2_route)
        http2_retry_policy = get_http_retry_policy_from_route(_http2_route)
        http2_timeout = get_timeout_from_route(_http2_route)

        http2_route = HttpRoute(
            action=http2_action,
            match=http2_match,
            retry_policy=http2_retry_policy,
            timeout=http2_timeout,
        )

    if _tcp_route is not None:
        tcp_action = get_action_from_route(_tcp_route)
        tcp_timeout = get_timeout_from_route(_tcp_route)

        _tcp_match = _tcp_route.get("match")
        tcp_match = None
        if _tcp_match is not None:
            tcp_match = TCPRouteMatch(port=_tcp_match.get("port"))

        tcp_route = TCPRoute(action=tcp_action, match=tcp_match, timeout=tcp_timeout)

    return RouteSpec(
        grpc_route=grpc_route,
        http_route=http_route,
        http2_route=http2_route,
        priority=spec.get("priority"),
        tcp_route=tcp_route,
    )
