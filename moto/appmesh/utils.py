from typing import Any, List, Optional

from moto.appmesh.dataclasses.route import (
    GrpcMetadatum,
    GrpcRouteMatch,
    HttpRouteMatch,
    HttpRouteRetryPolicy,
    Match,
    QueryParameterMatch,
    Range,
    RouteAction,
    RouteActionWeightedTarget,
    RouteMatchPath,
    RouteMatchQueryParameter,
    Timeout,
    TimeValue,
)
from moto.appmesh.dataclasses.virtual_router import PortMapping


def port_mappings_from_spec(self, spec: Any) -> List[PortMapping]:  # type: ignore[misc]
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
            path = RouteMatchPath(exact=_path.get("exact"), regex=path.get("regex"))
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
        method=_route_match.get("method"),
        path=path,
        port=_route_match.get("port"),
        prefix=_route_match.get("port"),
        query_parameters=query_parameters,
        scheme=_route_match.get("scheme"),
    )


def get_http_retry_policy_from_route(route: Any) -> Optional[HttpRouteRetryPolicy]:  # type: ignore[misc]
    _per_retry_timeout = route.get("perRetryTimeout")
    per_retry_timeout = TimeValue(
        unit=_per_retry_timeout.get("unit"), value=_per_retry_timeout.get("value")
    )
    return HttpRouteRetryPolicy(
        max_retries=route.get("maxRetries"),
        http_retry_events=route.get("httpRetryEvents"),
        per_retry_timeout=per_retry_timeout,
        tcp_retry_events=route.get("tcpRetryEvents"),
    )


def get_timeout_from_route(route: Any) -> Optional[Timeout]:  # type: ignore[misc]
    _timeout = route.get("timeout") or {}
    idle, per_request = None, None
    _idle = _timeout.get("idle")
    if _idle is not None:
        idle = TimeValue(unit=_idle.get("unit"), value=_idle.get("value"))
    _per_request = _timeout.get("per_request")
    if _per_request is not None:
        per_request = TimeValue(
            unit=_per_request.get("unit"), value=_per_request.get("value")
        )
    return (
        Timeout(idle=idle, per_request=per_request)
        if idle is not None or per_request is not None
        else None
    )
