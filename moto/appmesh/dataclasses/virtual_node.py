from dataclasses import asdict, dataclass, field
from typing import Dict, List, Literal, Optional

from moto.appmesh.dataclasses.shared import MissingField, Status, TimeValue, Timeout
from moto.appmesh.utils import clean_dict


@dataclass
class CertificateFile:
    certificate_chain: str

    def to_dict(self):
        return {
            "certificateChain": self.certificate_chain
        }

@dataclass
class CertificateFileWithPrivateKey(CertificateFile):
    private_key: str

    def to_dict(self):
        return {
            "certificateChain": self.certificate_chain,
            "privateKey": self.private_key
        }

@dataclass
class SDS:
    secret_name: str

    def to_dict(self):
        return {
            "secretName": self.secret_name
        }
    

@dataclass
class Certificate:
    file:  Optional[CertificateFileWithPrivateKey]
    sds:  Optional[SDS]
    
    def to_dict(self):
        return clean_dict({
            "file": (self.file or MissingField()).to_dict(),
            "sds": (self.sds or MissingField()).to_dict()
        })

@dataclass
class ListenerCertificateACM:
    certificate_arn: str

    def to_dict(self):
        return {"certificateArn": self.certificate_arn}

@dataclass
class TLSListenerCertificate(Certificate):
    acm: Optional[ListenerCertificateACM]

    def to_dict(self):
        return clean_dict({
            "acm": (self.acm or MissingField()).to_dict(),
            "file": (self.file or MissingField()).to_dict(),
            "sds": (self.sds or MissingField()).to_dict()
        })

@dataclass
class Match:
    exact: List[str]

    to_dict=asdict

@dataclass
class SubjectAlternativeNames:
    match: Match

    def to_dict(self):
        return {
            "match": self.match.to_dict()
        }

@dataclass
class ACM:
    certificate_authority_arns: List[str]

    def to_dict(self):
        return {
            "certificateAuthorityArns": self.certificate_authority_arns
        }

@dataclass
class Trust:
    file: Optional[CertificateFile]
    sds: Optional[SDS]

    def to_dict(self):
        return clean_dict({
            "file": (self.file or MissingField()).to_dict(),
            "sds": (self.sds or MissingField()).to_dict(),
        })

@dataclass
class BackendTrust(Trust):
    acm: Optional[ACM]

    def to_dict(self):
        return clean_dict({
            "acm": (self.acm or MissingField()).to_dict(), 
            "file": (self.file or MissingField()).to_dict(),
            "sds": (self.sds or MissingField()).to_dict(),
        })

@dataclass
class Validation:
    subject_alternative_names: Optional[SubjectAlternativeNames]

    def to_dict(self):
        return clean_dict({ "subjectAlternativeNames": (self.subject_alternative_names or MissingField()).to_dict() })

@dataclass
class TLSBackendValidation(Validation):
    trust: BackendTrust

    def to_dict(self):
        return clean_dict({ 
            "subjectAlternativeNames": (self.subject_alternative_names or MissingField()).to_dict(),
            "trust": self.trust.to_dict()
        })

@dataclass
class TLSListenerValidation(Validation):
    trust: Trust

    def to_dict(self):
        return clean_dict({ 
            "subjectAlternativeNames": (self.subject_alternative_names or MissingField()).to_dict(),
            "trust": self.trust.to_dict()
        })

@dataclass
class TLSClientPolicy:
    certificate: Optional[Certificate]
    enforce: Optional[bool]
    ports: Optional[List[int]]
    validation: TLSBackendValidation

    def to_dict(self):
        return clean_dict({
            "certificate": (self.certificate or MissingField()).to_dict(),
            "enforce": self.enforce,
            "ports": self.ports,
            "validation": self.validation.to_dict()
        })

@dataclass
class ClientPolicy:
    tls: Optional[TLSClientPolicy]

    def to_dict(self):
        return clean_dict({
            "tls": (self.tls or MissingField()).to_dict()
        })

@dataclass
class BackendDefaults:
    client_policy: Optional[ClientPolicy]

    def to_dict(self):
        return clean_dict({
            "clientPolicy": (self.client_policy or MissingField()).to_dict()
        })

@dataclass
class VirtualService:
    client_policy: Optional[ClientPolicy]
    virtual_service_name: str

    def to_dict(self):
        return clean_dict({
            "clientPolicy": (self.client_policy or MissingField()).to_dict(),
            "virtualServiceName": self.virtual_service_name
        })

@dataclass
class Backend:
    virtual_service: Optional[VirtualService]

    def to_dict(self):
        return clean_dict({
            "virtualService": (self.virtual_service or MissingField()).to_dict()
        })

@dataclass
class HTTPConnection:
    max_connections: int
    max_pending_requests: Optional[int]

    def to_dict(self):
        return clean_dict({
            "maxConnections": self.max_connections,
            "maxPendingRequests": self.max_pending_requests
        })

@dataclass
class GRPCOrHTTP2Connection:
    max_requests: int

    def to_dict(self):
        return { "maxRequests": self.max_requests }

@dataclass
class TCPConnection:
    max_connections: int

    def to_dict(self):
        return { "maxConnections": self.max_connections }

@dataclass
class ConnectionPool:
    grpc: Optional[GRPCOrHTTP2Connection]
    http: Optional[HTTPConnection]
    http2: Optional[GRPCOrHTTP2Connection]
    tcp: Optional[TCPConnection]

    def to_dict(self):
        return clean_dict({
            "grpc": (self.grpc or MissingField()).to_dict(),
            "http": (self.http or MissingField()).to_dict(),
            "http2": (self.http2 or MissingField()).to_dict(),
            "tcp": (self.tcp or MissingField()).to_dict(),
        })

@dataclass
class HealthCheck:
    healthy_threshold: int
    interval_millis: int
    path: Optional[str]
    port: Optional[int]
    protocol: str
    timeout_millis: int
    unhealthy_threshold: int

    def to_dict(self):
        return clean_dict({
            "healthyThreshold": self.healthy_threshold,
            "intervalMillis": self.interval_millis,
            "path": self.path,
            "port": self.port,
            "protocol": self.protocol,
            "timeoutMillis": self.timeout_millis,
            "unhealthyThreshold": self.unhealthy_threshold
        })

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
    to_dict=asdict

@dataclass
class TCPTimeout:
    idle: TimeValue

    def to_dict(self):
        return {"idle": self.idle.to_dict()}

@dataclass
class ProtocolTimeouts:
    grpc: Optional[Timeout]
    http: Optional[Timeout]
    http2: Optional[Timeout]
    tcp: Optional[TCPTimeout]

    def to_dict(self):
        return clean_dict({
            "grpc": (self.grpc or MissingField()).to_dict(),
            "http": (self.http or MissingField()).to_dict(),
            "http2": (self.http2 or MissingField()).to_dict(),
            "tcp": (self.tcp or MissingField()).to_dict(),
        }) 

@dataclass
class ListenerTLS:
    certificate: TLSListenerCertificate
    mode: str
    validation: Optional[TLSListenerValidation]

    def to_dict(self):
        return clean_dict({
            "certificate": self.certificate.to_dict(),
            "mode": self.mode,
            "validation": (self.validation or MissingField()).to_dict()
        })

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
