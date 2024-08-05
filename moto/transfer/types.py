from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, TypedDict

from moto.core.common_models import BaseModel


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

    def to_dict(self) -> Dict[str, Any]:
        user = {
            "HomeDirectory": self.home_directory,
            "HomeDirectoryType": self.home_directory_type,
            "Policy": self.policy,
            "Role": self.role,
            "UserName": self.user_name,
            "Arn": self.arn,
            "HomeDirectoryMappings": [
                {
                    "Entry": mapping.get("entry"),
                    "Target": mapping.get("target"),
                    "Type": mapping.get("type"),
                }
                for mapping in self.home_directory_mappings
            ],
            "Tags": self.tags,
        }
        if self.posix_profile:
            user.update(
                {
                    "PosixProfile": {
                        "Uid": self.posix_profile.get("uid"),
                        "Gid": self.posix_profile.get("gid"),
                        "SecondaryGids": self.posix_profile.get("secondary_gids"),
                    }
                }
            )
        if len(self.ssh_public_keys) > 0:
            user.update(
                {
                    "SshPublicKeys": [
                        {
                            "DateImported": key.get("date_imported"),
                            "SshPublicKeyBody": key.get("ssh_public_key_body"),
                            "SshPublicKeyId": key.get("ssh_public_key_id"),
                        }
                        for key in self.ssh_public_keys
                    ]
                }
            )
        return user


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
    passive_ip: str
    tls_session_resumption_mode: ServerProtocolTlsSessionResumptionMode
    set_stat_option: ServerSetStatOption
    as2_transports: List[Literal["HTTP"]]


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

    def to_dict(self) -> Dict[str, Any]:
        server = {
            "Certificate": self.certificate,
            "Domain": self.domain,
            "EndpointType": self.endpoint_type,
            "HostKeyFingerprint": self.host_key_fingerprint,
            "IdentityProviderType": self.identity_provider_type,
            "LoggingRole": self.logging_role,
            "PostAuthenticationLoginBanner": self.post_authentication_login_banner,
            "PreAuthenticationLoginBanner": self.pre_authentication_login_banner,
            "Protocols": self.protocols,
            "SecurityPolicyName": self.security_policy_name,
            "StructuredLogDestinations": self.structured_log_destinations,
            "Arn": self.arn,
            "As2ServiceManagedEgressIpAddresses": self.as2_service_managed_egress_ip_addresses,
            "ServerId": self.server_id,
            "State": self.state,
            "Tags": self.tags,
            "UserCount": self.user_count,
        }
        if self.endpoint_details is not None:
            server.update(
                {
                    "EndpointDetails": {
                        "AddressAllocationIds": self.endpoint_details.get(
                            "address_allocation_ids"
                        ),
                        "SubnetIds": self.endpoint_details.get("subnet_ids"),
                        "VpcEndpointId": self.endpoint_details.get("vpc_endpoint_id"),
                        "VpcId": self.endpoint_details.get("vpc_id"),
                        "SecurityGroupIds": self.endpoint_details.get(
                            "security_group_ids"
                        ),
                    }
                }
            )
        if self.identity_provider_details is not None:
            server.update(
                {
                    "IdentityProviderDetails": {
                        "Url": self.identity_provider_details.get("url"),
                        "InvocationRole": self.identity_provider_details.get(
                            "invocation_role"
                        ),
                        "DirectoryId": self.identity_provider_details.get(
                            "directory_id"
                        ),
                        "Function": self.identity_provider_details.get("function"),
                        "SftpAuthenticationMethods": self.identity_provider_details.get(
                            "sftp_authentication_methods"
                        ),
                    }
                }
            )
        if self.protocol_details is not None:
            server.update(
                {
                    "ProtocolDetails": {
                        "PassiveIp": self.protocol_details.get("passive_ip"),
                        "TlsSessionResumptionMode": self.protocol_details.get(
                            "tls_session_resumption_mode"
                        ),
                        "SetStatOption": self.protocol_details.get("set_stat_option"),
                        "As2Transports": self.protocol_details.get("as2_transports"),
                    }
                }
            )
        if self.s3_storage_options is not None:
            server.update(
                {
                    "S3StorageOptions": {
                        "DirectoryListingOptimization": self.s3_storage_options.get(
                            "directory_listing_optimization"
                        )
                    }
                }
            )
        if self.workflow_details is not None:
            server.update(
                {
                    "WorkflowDetails": {
                        "OnUpload": [
                            {
                                "WorkflowId": workflow.get("workflow_id"),
                                "ExecutionRole": workflow.get("execution_role"),
                            }
                            for workflow in self.workflow_details.get("on_upload")
                        ],
                        "OnPartialUpload": [
                            {
                                "WorkflowId": workflow.get("workflow_id"),
                                "ExecutionRole": workflow.get("execution_role"),
                            }
                            for workflow in self.workflow_details.get(
                                "on_partial_upload"
                            )
                        ],
                    }
                }
            )
        return server
