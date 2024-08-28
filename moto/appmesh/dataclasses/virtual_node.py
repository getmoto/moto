from dataclasses import dataclass, field
from typing import Dict, List, Optional

from moto.appmesh.dataclasses.shared import Status


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
    acm: Optional[ACM]
    file: Optional[CertificateFile]
    sds: Optional[SDS]

@dataclass
class TLSValidation:
    subject_alternative_names: Optional[SubjectAlternativeNames]
    trust: Trust


@dataclass
class TLSClientPolicy:
    certificate: Optional[Certificate]
    enforce: Optional[bool]
    ports: Optional[List[int]]
    validation: TLSValidation

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
class VirtualNodeSpec:
    backend_defaults: Optional[BackendDefaults]
    backends: Optional[List[Backend]]
    # listeners:
    # logging:
    # service_discovery:
    tags: Optional[List[Dict[str, str]]]
    virtual_node_name: str
    status: Status = field(default_factory=lambda: {"status": "ACTIVE"})
