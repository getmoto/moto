from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def clean_dict(obj: Dict[str, Any]):  # type: ignore[misc]
    return {
        key: value for key, value in obj.items() if value is not None and value != []
    }


class MissingField:
    def to_dict(self) -> None:
        return


@dataclass
class TimeValue:
    unit: str
    value: int
    to_dict = asdict


@dataclass
class RouteActionWeightedTarget:
    port: Optional[int] = field(default=None)
    virtual_node: str
    weight: int

    def to_dict(self):
        return clean_dict(
            {"port": self.port, "virtualNode": self.virtual_node, "weight": self.weight}
        )


@dataclass
class RouteAction:
    weighted_targets: List[RouteActionWeightedTarget]

    def to_dict(self):
        return clean_dict(
            {"weightedTargets": [target.to_dict() for target in self.weighted_targets]}
        )


@dataclass
class Range:
    start: int
    end: int
    to_dict = asdict


@dataclass
class Match:
    exact: Optional[str]
    prefix: Optional[str]
    range: Optional[Range]
    regex: Optional[str]
    suffix: Optional[str]

    def to_dict(self):
        return clean_dict(
            {
                "exact": self.exact,
                "prefix": self.prefix,
                "range": (self.range or MissingField()).to_dict(),
                "regex": self.regex,
                "suffix": self.suffix,
            }
        )


@dataclass
class GrpcMetadata:
    invert: Optional[bool]
    match: Optional[Match]
    name: str

    def to_dict(self):
        return clean_dict(
            {
                "invert": self.invert,
                "match": (self.match or MissingField()).to_dict(),
                "name": self.name,
            }
        )


# same object, just different name
HttpRouteMatchHeader = GrpcMetadata


@dataclass
class RouteMatchPath:
    exact: str
    regex: str
    to_dict = asdict


@dataclass
class QueryParameterMatch:
    exact: str
    to_dict = asdict


@dataclass
class RouteMatchQueryParameter:
    match: Optional[QueryParameterMatch] = field(default=None)
    name: str

    def to_dict(self):
        return clean_dict(
            {"match": (self.match or MissingField()).to_dict(), "name": self.name}
        )


@dataclass
class HttpRouteMatch:
    headers: Optional[List[HttpRouteMatchHeader]] = field(default=None)
    method: Optional[str] = field(default=None)
    path: Optional[RouteMatchPath] = field(default=None)
    port: Optional[int] = field(default=None)
    prefix: Optional[str] = field(default=None)
    query_parameters: Optional[List[RouteMatchQueryParameter]] = field(default=None)
    scheme: Optional[str] = field(default=None)

    def to_dict(self):
        return clean_dict(
            {
                "headers": [header.to_dict() for header in self.headers or []],
                "method": self.method,
                "path": (self.path or MissingField()).to_dict(),
                "port": self.port,
                "prefix": self.prefix,
                "queryParameters": [
                    param.to_dict() for param in self.query_parameters or []
                ],
                "scheme": self.scheme,
            }
        )


@dataclass
class RouteRetryPolicy:
    http_retry_events: Optional[List[str]]
    max_retries: int
    per_retry_timeout: TimeValue
    tcp_retry_events: Optional[List[str]]

    def to_dict(self):
        return clean_dict(
            {
                "httpRetryEvents": self.http_retry_events or [],
                "maxRetries": self.max_retries,
                "perRetryTimeout": self.per_retry_timeout.to_dict(),
                "tcpRetryEvents": self.tcp_retry_events or [],
            }
        )


@dataclass
class Timeout:
    idle: Optional[TimeValue] = field(default=None)
    per_request: Optional[TimeValue] = field(default=None)

    def to_dict(self):
        return clean_dict(
            {
                "idle": (self.idle or MissingField).to_dict(),
                "perRequest": (self.per_request or MissingField).to_dict(),
            }
        )


@dataclass
class GrpcRouteMatch:
    metadata: Optional[List[GrpcMetadata]]
    method_name: Optional[str]
    port: Optional[int]
    service_name: Optional[str]

    def to_dict(self):
        return clean_dict(
            {
                "metadata": [meta.to_dict() for meta in self.metadata or []],
                "methodName": self.method_name,
                "port": self.port,
                "serviceName": self.service_name,
            }
        )


@dataclass
class GrcpRouteRetryPolicy:
    grpc_retry_events: Optional[List[str]]
    http_retry_events: Optional[List[str]]
    max_retries: int
    per_retry_timeout: TimeValue
    tcp_retry_events: Optional[List[str]]

    def to_dict(self):
        return clean_dict(
            {
                "grpcRetryEvents": self.tcp_retry_events or [],
                "httpRetryEvents": self.tcp_retry_events or [],
                "maxRetries": self.max_retries,
                "perRetryTimeout": self.per_retry_timeout,
                "tcpRetryEvents": self.tcp_retry_events or [],
            }
        )


@dataclass
class GrpcRoute:
    action: RouteAction
    match: GrpcRouteMatch
    retry_policy: Optional[GrcpRouteRetryPolicy]
    timeout: Optional[Timeout]

    def to_dict(self):
        return clean_dict(
            {
                "action": self.action,
                "match": self.match,
                "retryPolicy": (self.retry_policy or MissingField()).to_dict(),
                "timeout": (self.timeout or MissingField()).to_dict(),
            }
        )


@dataclass
class HttpRoute:
    action: RouteAction
    match: HttpRouteMatch
    retry_policy: Optional[RouteRetryPolicy] = field(default=None)
    timeout: Optional[Timeout] = field(default=None)

    def to_dict(self):
        return clean_dict(
            {
                "action": self.action,
                "match": self.match,
                "retryPolicy": (self.retry_policy or MissingField()).to_dict(),
                "timeout": (self.timeout or MissingField()).to_dict(),
            }
        )


@dataclass
class TCPRouteMatch:
    port: int
    to_dict = asdict


@dataclass
class TCPRoute:
    action: RouteAction
    match: Optional[TCPRouteMatch]
    timeout: Optional[Timeout]

    def to_dict(self):
        return clean_dict(
            {
                "action": self.action,
                "match": (self.match or MissingField()).to_dict(),
                "timeout": (self.timeout or MissingField()).to_dict(),
            }
        )


@dataclass
class RouteSpec:
    grcp_route: Optional[GrpcRoute] = field(default=None)
    http_route: Optional[HttpRoute] = field(default=None)
    http2_route: Optional[HttpRoute] = field(default=None)
    priority: Optional[int]
    tcp_route: Optional[TCPRoute] = field(default=None)

    def to_dict(self):
        spec = {
            "grcpRoute": (self.grcp_route or MissingField()).to_dict(),
            "httpRoute": (self.grcp_route or MissingField()).to_dict(),
            "http2Route": (self.grcp_route or MissingField()).to_dict(),
            "priority": self.priority,
            "tcpRoute": (self.tcp_route or MissingField()).to_dict(),
        }
        return clean_dict(spec)
