from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional, TypedDict

from moto.core.common_models import BaseModel
from moto.utilities.utils import dataclass_to_camel_case_dict


class UserHomeDirectoryType(str, Enum):
    PATH = "PATH"
    LOGICAL = "LOGICAL"


class UserHomeDirectoryMappingType(str, Enum):
    FILE = "FILE"
    DIRECTORY = "DIRECTORY"


class UserHomeDirectoryMapping(TypedDict):
    entry: str
    target: str
    type: Optional[UserHomeDirectoryMappingType]


class UserPosixProfile(TypedDict):
    uid: int
    gid: int
    secondary_gids: Optional[List[int]]


class UserSshPublicKey(TypedDict):
    date_imported: str
    ssh_public_key_body: str
    ssh_public_key_id: str


@dataclass
class User(BaseModel):
    home_directory: Optional[str]
    home_directory_mappings: Optional[List[UserHomeDirectoryMapping]]
    home_directory_type: Optional[UserHomeDirectoryType]
    policy: Optional[str]
    posix_profile: Optional[UserPosixProfile]
    role: str
    user_name: str
    arn: str = field(default="", init=False)
    ssh_public_keys: List[UserSshPublicKey] = field(default_factory=list)
    tags: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.arn == "":
            self.arn = f"arn:aws:transfer:{self.user_name}:{datetime.now().strftime('%Y%m%d%H%M%S')}"

    to_dict = dataclass_to_camel_case_dict


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


AS2_TRANSPORTS_TYPE = List[Literal["HTTP"]]


class ServerProtocolDetails(TypedDict):
    passive_ip: str
    tls_session_resumption_mode: ServerProtocolTlsSessionResumptionMode
    set_stat_option: ServerSetStatOption
    as2_transports: AS2_TRANSPORTS_TYPE


class ServerEndpointDetails(TypedDict):
    address_allocation_ids: List[str]
    subnet_ids: List[str]
    vpc_endpoint_id: str
    vpc_id: str
    security_group_ids: List[str]


class ServerIdentityProviderDetails(TypedDict):
    url: str
    invocation_role: str
    directory_id: str
    function: str
    sftp_authentication_methods: ServerIdentityProviderSftpAuthenticationMethods


class ServerWorkflowUpload(TypedDict):
    workflow_id: str
    execution_role: str


class ServerWorkflowDetails(TypedDict):
    on_upload: List[ServerWorkflowUpload]
    on_partial_upload: List[ServerWorkflowUpload]


class ServerS3StorageOptions(TypedDict):
    directory_listing_optimization: ServerS3StorageDirectoryListingOptimization


@dataclass
class Server(BaseModel):
    certificate: Optional[str]
    domain: Optional[ServerDomain]
    endpoint_details: Optional[ServerEndpointDetails]
    endpoint_type: Optional[ServerEndpointType]
    host_key_fingerprint: Optional[str]
    identity_provider_details: Optional[ServerIdentityProviderDetails]
    identity_provider_type: Optional[ServerIdentityProviderType]
    logging_role: Optional[str]
    post_authentication_login_banner: Optional[str]
    pre_authentication_login_banner: Optional[str]
    protocol_details: Optional[ServerProtocolDetails]
    protocols: Optional[List[ServerProtocols]]
    s3_storage_options: Optional[ServerS3StorageOptions]
    security_policy_name: Optional[str]
    structured_log_destinations: Optional[List[str]]
    workflow_details: Optional[ServerWorkflowDetails]
    arn: str = field(default="", init=False)
    as2_service_managed_egress_ip_addresses: List[str] = field(default_factory=list)
    server_id: str = field(default="", init=False)
    state: Optional[ServerState] = ServerState.ONLINE
    tags: List[Dict[str, str]] = field(default_factory=list)
    user_count: int = field(default=0)
    _users: List[User] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.arn == "":
            self.arn = f"arn:aws:transfer:{self.server_id}"
        if self.server_id == "":
            self.server_id = f"{self.identity_provider_type}:{self.server_id}:{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if self.as2_service_managed_egress_ip_addresses == []:
            self.as2_service_managed_egress_ip_addresses.append("0.0.0.0/0")

    to_dict = dataclass_to_camel_case_dict
