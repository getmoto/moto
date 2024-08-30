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
)
from moto.appmesh.dataclasses.shared import Timeout, TimeValue
from moto.appmesh.dataclasses.virtual_node import (
    ACM,
    DNS,
    SDS,
    AWSCloudMap,
    BackendDefaults,
    BackendTrust,
    Certificate,
    CertificateFile,
    CertificateFileWithPrivateKey,
    ClientPolicy,
    ConnectionPool,
    GRPCOrHTTP2Connection,
    HTTPConnection,
    HealthCheck,
    KeyValue,
    Listener,
    ListenerCertificateACM,
    ListenerTLS,
    OutlierDetection,
    ProtocolTimeouts,
    ServiceDiscovery,
    SubjectAlternativeNames,
    TCPConnection,
    TCPTimeout,
    TLSBackendValidation,
    TLSClientPolicy,
    TLSListenerCertificate,
    TLSListenerValidation,
    Trust,
    VirtualNodeSpec,
)
from moto.appmesh.dataclasses.virtual_node import (
    Match as VirtualNodeMatch,
)
from moto.appmesh.dataclasses.virtual_router import PortMapping
from moto.appmesh.exceptions import (
    MeshNotFoundError,
    MeshOwnerDoesNotMatchError,
    MissingRequiredFieldError,
    RouteNameAlreadyTakenError,
    RouteNotFoundError,
    VirtualRouterNameAlreadyTakenError,
    VirtualRouterNotFoundError,
)


def clean_dict(obj: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore[misc]
    return {
        key: value for key, value in obj.items() if value is not None and value != []
    }


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


def build_route_spec(spec: Dict[str, Any]) -> RouteSpec:  # type: ignore[misc]
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


def build_virtual_node_spec(spec: Dict[str, Any]) -> VirtualNodeSpec:  # type: ignore[misc]
    _backend_defaults = spec.get("backendDefaults")
    _backends = spec.get("backends")
    _listeners = spec.get("listeners")
    _logging = spec.get("logging")
    _service_discovery = spec.get("serviceDiscovery")

    backend_defaults, backends, listeners, logging, service_discovery = (
        None,
        None,
        None,
        None,
        None,
    )

    if _backend_defaults is not None:
        _client_policy = _backend_defaults.get("clientPolicy")
        client_policy = None
        if _client_policy is not None:
            _tls = _client_policy.get("tls")
            tls = None
            if _tls is not None:
                _certificate = _tls.get("certificate")
                _validation = _tls.get("validation")
                certificate, validation = None, None
                if _certificate is not None:
                    _file = _certificate.get("file")
                    _sds = _certificate.get("sds")
                    file, sds = None, None
                    if _file is not None:
                        file = CertificateFileWithPrivateKey(
                            certificate_chain=_file.get("certificateChain"),
                            private_key=_file.get("privateKey"),
                        )
                    if _sds is not None:
                        sds = SDS(secret_name=_sds.get("secretName"))
                    certificate = Certificate(file=file, sds=sds)
                if _validation is None:
                    raise MissingRequiredFieldError("validation")
                _subject_alternative_names = _validation.get("subjectAlternativeNames")
                _trust = _validation.get("trust")
                subject_alternative_names = None

                if _subject_alternative_names is not None:
                    match = VirtualNodeMatch(
                        exact=(_subject_alternative_names.get("match") or {}).get(
                            "exact"
                        )
                        or []
                    )
                    subject_alternative_names = SubjectAlternativeNames(match=match)

                if _trust is None:
                    raise MissingRequiredFieldError("trust")

                _trust_file = _trust.get("file")
                _trust_sds = _trust.get("sds")
                _acm = _trust.get("acm")
                trust_file, trust_sds, acm = None, None, None
                if _trust_file is not None:
                    trust_file = CertificateFile(
                        certificate_chain=_trust_file.get("certificateChain")
                    )
                if _trust_sds is not None:
                    sds = SDS(secret_name=_sds.get("secretName"))
                if _acm is not None:
                    acm = ACM(
                        certificate_authority_arns=_acm.get("certificateAuthorityArns")
                    )
                trust = BackendTrust(file=trust_file, sds=trust_sds, acm=acm)

                validation = TLSBackendValidation(
                    subject_alternative_names=subject_alternative_names, trust=trust
                )
                tls = TLSClientPolicy(
                    certificate=certificate,
                    enforce=_tls.get("enforce"),
                    ports=_tls.get("ports"),
                    validation=validation,
                )
            client_policy = ClientPolicy(tls=tls)

        backend_defaults = BackendDefaults(client_policy=client_policy)

    if _listeners is not None:
        listeners = []
        for _listener in _listeners:
            _connection_pool = _listener.get("connectionPool")
            _health_check = _listener.get("healthCheck")
            _outlier_detection = _listener.get("outlierDetection")
            _port_mapping = _listener.get("portMapping")
            _timeout = _listener.get("timeout")
            _listener_tls = _listener.get("tls")
            (
                connection_pool,
                health_check,
                outlier_detection,
                port_mapping,
                timeout,
                listener_tls,
            ) = None, None, None, None, None, None

            if _connection_pool is not None:
                _grpc = _connection_pool.get("grpc")
                _http = _connection_pool.get("http")
                _http2 = _connection_pool.get("http2")
                _tcp = _connection_pool.get("tcp")
                grpc, http, http2, tcp = None, None, None, None

                if _grpc is not None:
                    grpc = GRPCOrHTTP2Connection(
                        max_requests= _grpc.get("maxRequests")
                    )
                if _http is not None:
                    http = HTTPConnection(
                        max_connections=_http.get("maxConnections")
                        max_pending_requests=_http.get("maxPendingRequests")
                    )
                if _http2 is not None:
                    http2 = GRPCOrHTTP2Connection(
                        max_requests=_http2.get("maxRequests")
                    )
                if _tcp is not None:
                    tcp = TCPConnection(
                        max_connections=_tcp.get("maxConnections")
                    )

                connection_pool = ConnectionPool(
                    grpc=grpc,
                    http=http,
                    http2=http2,
                    tcp=tcp
                )
            if _health_check is not None:
                health_check = HealthCheck(
                    healthy_threshold=_health_check.get("healthyThreshold"),
                    interval_millis=_health_check.get("intervalMillis"),
                    path=_health_check.get("path"),
                    port=_health_check.get("port"),
                    protocol=_health_check.get("protocol"),
                    timeout_millis=_health_check.get("timeoutMillis"),
                    unhealthy_threshold=_health_check.get("unhealthyThreshold")
                )
            
            if _outlier_detection is not None:
                _base_ejection_duration = _outlier_detection.get("baseEjectionDetection")
                _interval = _outlier_detection.get("interval")
                base_ejection_duration, interval = None, None
                if _base_ejection_duration is not None:
                    base_ejection_duration = TimeValue(
                        unit=_base_ejection_duration.get("unit"),
                        value=_base_ejection_duration.get("value")
                    ) 
                if _interval is not None:
                    interval = TimeValue(
                        unit=_interval.get("unit"),
                        value=_interval.get("value")
                    ) 
                outlier_detection = OutlierDetection(
                    base_ejection_duration=base_ejection_duration,
                    interval=interval,
                    max_ejection_percent=_outlier_detection.get("maxEjectionPercent"),
                    max_server_errors=_outlier_detection.get("maxServerErrors")
                )
            
            if _port_mapping is not None:
                port_mapping = PortMapping(
                    port=_port_mapping.get("port"),
                    protocol=_port_mapping.get("protocol") 
                )
            
            if _timeout is not None:
                _grpc_timeout = _timeout.get("grpc")
                _http_timeout = _timeout.get("http")
                _http2_timeout = _timeout.get("http2")
                _tcp_timeout = _timeout.get("tpc")
                grpc_timeout, http_timeout, http2_timeout, tcp_timeout = None, None, None, None

                if _grpc_timeout is not None:
                    _idle = _grpc_timeout.get("idle")
                    _per_request = _grpc_timeout.get("perRequest")
                    idle, per_request = None, None
                    if _idle is not None:
                        idle = TimeValue(
                            unit=_idle.get("unit"),
                            value=_idle.get("value")
                        )
                    if _per_request is not None:
                        per_request = TimeValue(
                            unit=_per_request.get("unit"),
                            value=_per_request.get("value")
                        )
                    grpc_timeout = Timeout(
                        idle=idle,
                        per_request=per_request
                    )
                if _http_timeout is not None: 
                    _idle = _http_timeout.get("idle")
                    _per_request = _http_timeout.get("perRequest")
                    idle, per_request = None, None
                    if _idle is not None:
                        idle = TimeValue(
                            unit=_idle.get("unit"),
                            value=_idle.get("value")
                        )
                    if _per_request is not None:
                        per_request = TimeValue(
                            unit=_per_request.get("unit"),
                            value=_per_request.get("value")
                        )
                    http_timeout = Timeout(
                        idle=idle,
                        per_request=per_request
                    )
                if _http2_timeout is not None:
                    _idle = _http2_timeout.get("idle")
                    _per_request = _http2_timeout.get("perRequest")
                    idle, per_request = None, None
                    if _idle is not None:
                        idle = TimeValue(
                            unit=_idle.get("unit"),
                            value=_idle.get("value")
                        )
                    if _per_request is not None:
                        per_request = TimeValue(
                            unit=_per_request.get("unit"),
                            value=_per_request.get("value")
                        )
                    http2_timeout = Timeout(
                        idle=idle,
                        per_request=per_request
                    ) 
                if _tcp_timeout is not None:
                    _idle = _tcp_timeout.get("idle")
                    idle = None
                    if _idle is not None:
                        idle = TimeValue(
                            unit=_idle.get("unit"),
                            value=_idle.get("value")
                        )
                    tcp_timeout = TCPTimeout(
                        idle=idle
                    )

                timeout = ProtocolTimeouts(
                    grpc=grpc_timeout,
                    http=http_timeout,
                    http2=http2_timeout,
                    tcp=tcp_timeout
                )
            
            if _listener_tls is not None:
                _tls_listener_certificate = _listener_tls.get("certificate") 
                _tls_listener_validation = _listener_tls.get("validation") 
                tls_listener_certificate, tls_listener_validation = None, None
                if _tls_listener_certificate is not None:
                    _listener_certificate_file = _tls_listener_certificate.get("file")
                    _listener_certificate_sds = _tls_listener_certificate.get("sds")
                    _listener_certificate_acm = _tls_listener_certificate.get("acm")
                    listener_certificate_file, listener_certificate_sds, listener_certificate_acm = None, None, None
                    if _listener_certificate_file is not None:
                        listener_certificate_file = CertificateFileWithPrivateKey(
                            certificate_chain=_listener_certificate_file.get("certificateChain"),
                            private_key=_listener_certificate_file.get("privateKey")
                        )
                    if _listener_certificate_sds is not None:
                        listener_certificate_sds = SDS(
                            secret_name=_listener_certificate_sds.get("secretName")
                        ) 
                    if _listener_certificate_acm is not None:
                        listener_certificate_acm = ListenerCertificateACM(
                            certificate_arn=_listener_certificate_acm.get("certificateArn")
                        )

                    certificate = TLSListenerCertificate(
                        file=listener_certificate_file,
                        sds=listener_certificate_sds,
                        acm=listener_certificate_acm
                    )
                if _tls_listener_validation is not None:
                    _subject_alternative_names = _tls_listener_validation.get("subjectAlternativeNames") 
                    _trust = _tls_listener_validation.get("trust")
                    subject_alternative_names, tls_listener_trust = None, None
                    if _subject_alternative_names is not None:
                        _tls_listener_match = _subject_alternative_names.get("match") 
                        tls_listener_match = VirtualNodeMatch(
                            exact=_tls_listener_match.get("exact")
                        )
                        subject_alternative_names = SubjectAlternativeNames(
                            match=tls_listener_match
                        )
                    if _trust is not None:
                        _tls_listener_certificate_file = _trust.get("file")
                        _tls_listener_sds = _trust.get("sds") 
                        tls_listener_certificate_file, tls_listener_sds = None, None
                        if _tls_listener_certificate_file is not None:
                            tls_listener_certificate_file = CertificateFile(
                                certificate_chain=_tls_listener_certificate_file.get("certificateChain")
                            )
                        if _tls_listener_sds is not None:
                            tls_listener_sds = SDS(
                                secret_name=_tls_listener_sds.get("secretName")
                            )
                        tls_listener_trust = Trust(
                            file=tls_listener_certificate_file,
                            sds=tls_listener_sds
                        )


                    validation = TLSListenerValidation(
                        subject_alternative_names=subject_alternative_names,
                        trust=tls_listener_trust
                    )
                listener_tls = ListenerTLS(
                    certificate=tls_listener_certificate,
                    mode=_listener_tls.get("mode"),
                    validation=tls_listener_validation
                )

            listener = Listener(
                connection_pool=connection_pool, 
                health_check=health_check,
                outlier_detection=outlier_detection,
                port_mapping=port_mapping,
                timeout=timeout,
                listener_tls=listener_tls
            )
            listeners.append(listener)

    if _service_discovery is not None:
        _aws_cloud_map = _service_discovery.get("awsCloudMap")
        _dns = _service_discovery.get("dns")
        aws_cloud_map, dns = None, None
        if _aws_cloud_map is not None:
            _attributes = _aws_cloud_map.get("attributes")
            if _attributes is None:
                raise MissingRequiredFieldError("attributes")
            attributes = [
                KeyValue(key=attribute.get("key"), value=attribute.get("value"))
                for attribute in _attributes
            ]
            aws_cloud_map = AWSCloudMap(
                attributes=attributes,
                ip_preference=_aws_cloud_map.get("ipPreference"),
                namespace_name=_aws_cloud_map.get("namespaceName"),
                service_name=_aws_cloud_map.get("serviceName"),
            )
        if _dns is not None:
            dns = DNS(
                hostname=_dns.get("hostname"),
                ip_preference=_dns.get("ipPreference"),
                response_type=_dns.get("responseType"),
            )
        service_discovery = ServiceDiscovery(aws_cloud_map=aws_cloud_map, dns=dns)

    return VirtualNodeSpec(
        backend_defaults=backend_defaults,
        backends=backends,
        listeners=listeners,
        logging=logging,
        service_discovery=service_discovery,
    )
