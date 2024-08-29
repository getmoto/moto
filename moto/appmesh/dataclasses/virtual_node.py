from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

from moto.appmesh.dataclasses.shared import Status, TimeValue, Timeout


@dataclass
class CertificateFile:
    certificate_chain: str

@dataclass
class CertificateFileWithPrivateKey(CertificateFile):
    private_key: str

@dataclass
class SDS:
    secret_name: str

@dataclass
class Certificate:
    file:  Optional[CertificateFileWithPrivateKey]
    sds:  Optional[SDS]

@dataclass
class TLSListenerCertificate(Certificate):
    acm: Optional[Dict[Literal["certificate_arn"], str]]

@dataclass
class Match:
    exact: List[str]

@dataclass
class SubjectAlternativeNames:
    match: Match

@dataclass
class ACM:
    certificate_authority_arns: List[str]

@dataclass
class Trust:
    file: Optional[CertificateFile]
    sds: Optional[SDS]

@dataclass
class BackendTrust(Trust):
    acm: Optional[ACM]

@dataclass
class Validation:
    subject_alternative_names: Optional[SubjectAlternativeNames]

@dataclass
class TLSBackendValidation(Validation):
    trust: BackendTrust 

@dataclass
class TLSListenerValidation(Validation):
    trust: Trust

@dataclass
class TLSClientPolicy:
    certificate: Optional[Certificate]
    enforce: Optional[bool]
    ports: Optional[List[int]]
    validation: TLSBackendValidation

@dataclass
class ClientPolicy:
    tls: Optional[TLSClientPolicy]

@dataclass
class BackendDefaults:
    client_policy: Optional[ClientPolicy]

@dataclass
class VirtualService:
    client_policy: Optional[ClientPolicy]
    virtual_service_name: str

@dataclass
class Backend:
    virtual_service: Optional[VirtualService]

@dataclass
class HTTPConnection:
    max_connections: int
    max_pending_requests: Optional[int]

@dataclass
class ConnectionPool:
    grpc: Optional[Dict[Literal["max_requests"], int]]
    http: HTTPConnection
    http2: Optional[Dict[Literal["max_requests"], int]]
    tcp: Optional[Dict[Literal["max_connections"], int]]

@dataclass
class HealthCheck:
    healthy_threshold: int
    interval_millis: int
    path: Optional[str]
    port: Optional[int]
    protocol: str
    timeout_millis: int
    unhealthy_threshold: int

@dataclass
class OutlierDetection:
    base_ejection_duration: TimeValue
    interval: TimeValue
    max_ejection_percent: int
    max_server_errors: int

@dataclass
class PortMapping:
    port: int
    protocol: str

@dataclass
class ProtocolTimeouts:
    grpc: Optional[Timeout]
    http: Optional[Timeout]
    http2: Optional[Timeout]
    tcp: Optional[Dict[Literal["idle"], TimeValue]]

@dataclass
class ListenerTLS:
    certificate: TLSListenerCertificate
    mode: str
    validation: Optional[TLSListenerValidation]

@dataclass
class Listener:
    connection_pool: Optional[ConnectionPool]
    health_check: Optional[HealthCheck]
    outlier_detection: Optional[OutlierDetection]
    port_mapping: PortMapping
    timeout: Optional[ProtocolTimeouts]
    tls: Optional[ListenerTLS]

@dataclass
class KeyValue:
    key: str
    value: str

@dataclass
class LoggingFormat:
    json: Optional[List[KeyValue]]
    text: Optional[str]

@dataclass
class AccessLogFile:
    format: Optional[LoggingFormat]
    path: str

@dataclass
class AccessLog:
    file: Optional[AccessLogFile]

@dataclass
class Logging:
    access_log: Optional[AccessLog]


@dataclass
class AWSCloudMap:
    attributes: Optional[List[KeyValue]]
    ip_preference: Optional[str]
    namespace_name: str
    service_name: str

@dataclass
class DNS:
    hostname: str
    ip_preference: Optional[str]
    response_type: Optional[str]

@dataclass
class ServiceDiscovery:
    aws_cloud_map: Optional[AWSCloudMap]
    dns: Optional[DNS]

@dataclass
class VirtualNodeSpec:
    backend_defaults: Optional[BackendDefaults]
    backends: Optional[List[Backend]]
    listeners: Optional[List[Listener]]
    logging: Optional[Logging]
    service_discovery: Optional[ServiceDiscovery]
    tags: Optional[List[Dict[str, str]]]
    virtual_node_name: str
    status: Status = field(default_factory=lambda: {"status": "ACTIVE"})
