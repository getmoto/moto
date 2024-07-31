from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, TypedDict

from moto.core.common_models import BaseModel


class UserHomeDirectoryType(str, Enum):
    PATH = "PATH"
    LOGICAL = "LOGICAL"


class UserHomeDirectoryMappingType(str, Enum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"


class UserHomeDirectoryMapping(TypedDict):
    Entry: str
    Target: str
    Type: Optional[UserHomeDirectoryMappingType]


class UserPosixProfile(TypedDict):
    Uid: int
    Gid: int
    SecondaryGids: Optional[List[int]]


class UserSshPublicKey(TypedDict):
    DateImported: str
    SshPublicKeyBody: str
    SshPublicKeyId: str


@dataclass
class User(BaseModel):
    HomeDirectory: Optional[str]
    HomeDirectoryType: Optional[UserHomeDirectoryType]
    Policy: Optional[str]
    PosixProfile: Optional[UserPosixProfile]
    Role: str
    UserName: str
    Arn: str = field(default="", init=False)
    HomeDirectoryMappings: List[UserHomeDirectoryMapping] = field(default_factory=list)
    SshPublicKeys: List[UserSshPublicKey] = field(default_factory=list)
    Tags: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.Arn == "":
            self.Arn = f"arn:aws:transfer:{self.UserName}:{datetime.now().strftime('%Y%m%d%H%M%S')}"

    to_dict = asdict


class ServerProtocolTlsSessionResumptionMode(str, Enum):
    DISABLED = "DISABLED"
    ENABLED = "ENABLED"
    ENFORCED = "ENFORCED"


class ServerSetStatOption(str, Enum):
    DEFAULT = "DEFAULT"
    ENABLE_NO_OP = "ENABLE_NO_OP"


class ServerDomain(str, Enum):
    S3 = "S3"
    EFS = "EFS"


class ServerEndpointType(str, Enum):
    PUBLIC = "PUBLIC"
    VPC = "VPC"
    VPC_ENDPOINT = "VPC_ENDPOINT"


class ServerIdentityProviderSftpAuthenticationMethods(str, Enum):
    PASSWORD = "PASSWORD"
    PUBLIC_KEY = "PUBLIC_KEY"
    PUBLIC_KEY_OR_PASSWORD = "PUBLIC_KEY_OR_PASSWORD"
    PUBLIC_KEY_AND_PASSWORD = "PUBLIC_KEY_AND_PASSWORD"


class ServerIdentityProviderType(str, Enum):
    SERVICE_MANAGED = "SERVICE_MANAGED"
    API_GATEWAY = "API_GATEWAY"
    AWS_DIRECTORY_SERVICE = "AWS_DIRECTORY_SERVICE"
    AWS_LAMBDA = "AWS_LAMBDA"


class ServerProtocols(str, Enum):
    SFTP = "SFTP"
    FTP = "FTP"
    FTPS = "FTPS"
    AS2 = "AS2"


class ServerState(str, Enum):
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    STARTING = "STARTING"
    STOPPING = "STOPPING"
    START_FAILED = "START_FAILED"
    STOP_FAILED = "STOP_FAILED"


class ServerS3StorageDirectoryListingOptimization(str, Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class ServerProtocolDetails(TypedDict):
    PassiveIp: str
    TlsSessionResumptionMode: ServerProtocolTlsSessionResumptionMode
    SetStatOption: ServerSetStatOption
    As2Transports: List[Literal["HTTP"]]


class ServerEndpointDetails(TypedDict):
    AddressAllocationIds: List[str]
    SubnetIds: List[str]
    VpcEndpointId: str
    VpcId: str
    SecurityGroupIds: List[str]


class ServerIdentityProviderDetails(TypedDict):
    Url: str
    InvocationRole: str
    DirectoryId: str
    Function: str
    SftpAuthenticationMethods: ServerIdentityProviderSftpAuthenticationMethods


class ServerWorkflowUpload(TypedDict):
    WorkflowId: str
    ExecutionRole: str


class ServerWorkflowDetails(TypedDict):
    OnUpload: ServerWorkflowUpload
    OnPartialUpload: ServerWorkflowUpload


class ServerS3StorageOptions(TypedDict):
    DirectoryListingOptimization: ServerS3StorageDirectoryListingOptimization


@dataclass
class Server(BaseModel):
    Certificate: Optional[str]
    Domain: Optional[ServerDomain]
    EndpointDetails: Optional[ServerEndpointDetails]
    EndpointType: Optional[ServerEndpointType]
    HostKeyFingerprint: Optional[str]
    IdentityProviderDetails: Optional[ServerIdentityProviderDetails]
    IdentityProviderType: Optional[ServerIdentityProviderType]
    LoggingRole: Optional[str]
    PostAuthenticationLoginBanner: Optional[str]
    PreAuthenticationLoginBanner: Optional[str]
    ProtocolDetails: Optional[ServerProtocolDetails]
    Protocols: Optional[List[ServerProtocols]]
    S3StorageOptions: Optional[ServerS3StorageOptions]
    SecurityPolicyName: Optional[str]
    State: Optional[ServerState]
    StructuredLogDestinations: Optional[List[str]]
    Tags: Optional[List[Dict[str, str]]]
    UserCount: Optional[int]
    WorkflowDetails: Optional[ServerWorkflowDetails]
    Arn: str = field(default="", init=False)
    As2ServiceManagedEgressIpAddresses: Optional[List[str]] = ["0.0.0.0"]
    ServerId: str = field(default="", init=False)
    Users: List[User] = []

    def __post_init__(self) -> None:
        if self.Arn == "":
            self.ServerId = f"{self.IdentityProviderType}:{self.ServerId}:{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.Arn = f"arn:aws:transfer:{self.ServerId}"

    to_dict = asdict
