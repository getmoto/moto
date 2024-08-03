"""TransferBackend class with methods for supported APIs."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
from moto.transfer.exceptions import PublicKeyNotFound, ServerNotFound, UserNotFound
from moto.transfer.types import UserPosixProfile

from .types import (
    Server,
    ServerDomain,
    ServerEndpointDetails,
    ServerEndpointType,
    ServerIdentityProviderDetails,
    ServerIdentityProviderType,
    ServerProtocolDetails,
    ServerProtocols,
    ServerS3StorageOptions,
    ServerWorkflowDetails,
    User,
    UserHomeDirectoryMapping,
    UserHomeDirectoryType,
    UserSshPublicKey,
)


class TransferBackend(BaseBackend):
    """Implementation of Transfer APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.servers: Dict[str, Server] = {}

    def create_server(
        self,
        certificate: Optional[str],
        domain: Optional[ServerDomain],
        endpoint_details: Optional[ServerEndpointDetails],
        endpoint_type: Optional[ServerEndpointType],
        host_key: str,
        identity_provider_details: Optional[ServerIdentityProviderDetails],
        identity_provider_type: Optional[ServerIdentityProviderType],
        logging_role: Optional[str],
        post_authentication_login_banner: Optional[str],
        pre_authentication_login_banner: Optional[str],
        protocols: Optional[List[ServerProtocols]],
        protocol_details: Optional[ServerProtocolDetails],
        security_policy_name: Optional[str],
        tags: Optional[List[Dict[str, str]]],
        workflow_details: Optional[ServerWorkflowDetails],
        structured_log_destinations: Optional[List[str]],
        s3_storage_options: Optional[ServerS3StorageOptions],
    ) -> str:
        server = Server(
            certificate=certificate,
            domain=domain,
            endpoint_details=endpoint_details,
            endpoint_type=endpoint_type,
            host_key_fingerprint=host_key,
            identity_provider_details=identity_provider_details,
            identity_provider_type=identity_provider_type,
            logging_role=logging_role,
            post_authentication_login_banner=post_authentication_login_banner,
            pre_authentication_login_banner=pre_authentication_login_banner,
            protocol_details=protocol_details,
            protocols=protocols,
            s3_storage_options=s3_storage_options,
            security_policy_name=security_policy_name,
            structured_log_destinations=structured_log_destinations,
            tags=(tags or []),
            workflow_details=workflow_details,
        )
        server_id = server.server_id
        self.servers[server_id] = server
        return server_id

    def describe_server(self, server_id: str) -> Server:
        if server_id not in self.servers:
            ServerNotFound(server_id=server_id)
        server = self.servers[server_id]
        return server

    def delete_server(self, server_id: str) -> None:
        if server_id not in self.servers:
            ServerNotFound(server_id=server_id)
        del self.servers[server_id]
        return

    def create_user(
        self,
        home_directory: Optional[str],
        home_directory_type: Optional[UserHomeDirectoryType],
        home_directory_mappings: List[UserHomeDirectoryMapping],
        policy: Optional[str],
        posix_profile: Optional[UserPosixProfile],
        role: str,
        server_id: str,
        ssh_public_key_body: Optional[str],
        tags: Optional[List[Dict[str, str]]],
        user_name: str,
    ) -> Tuple[str, str]:
        if server_id not in self.servers:
            ServerNotFound(server_id=server_id)
        user = User(
            home_directory=home_directory,
            home_directory_mappings=home_directory_mappings,
            home_directory_type=home_directory_type,
            policy=policy,
            posix_profile=posix_profile,
            role=role,
            tags=(tags or []),
            user_name=user_name,
        )
        if ssh_public_key_body is not None:
            now = datetime.now().strftime("%Y%m%d%H%M%S")
            ssh_public_keys: List[UserSshPublicKey] = [
                {
                    "date_imported": now,
                    "ssh_public_key_body": ssh_public_key_body,
                    "ssh_public_key_id": "mock_ssh_public_key_id_{ssh_public_key_body}_{now}",
                }
            ]
            user.ssh_public_keys = ssh_public_keys
        self.servers[server_id]._users.append(user)
        self.servers[server_id].user_count += 1
        return server_id, user_name

    def describe_user(self, server_id: str, user_name: str) -> Tuple[str, User]:
        if server_id not in self.servers:
            raise ServerNotFound(server_id=server_id)
        for user in self.servers[server_id]._users:
            if user.user_name == user_name:
                return server_id, user
        raise UserNotFound(user_name=user_name, server_id=server_id)

    def delete_user(self, server_id: str, user_name: str) -> None:
        if server_id not in self.servers:
            raise ServerNotFound(server_id=server_id)
        for i, user in enumerate(self.servers[server_id]._users):
            if user.user_name == user_name:
                del self.servers[server_id]._users[i]
                self.servers[server_id].user_count -= 1
                return
        raise UserNotFound(server_id=server_id, user_name=user_name)

    def import_ssh_public_key(
        self, server_id: str, ssh_public_key_body: str, user_name: str
    ) -> Tuple[str, str, str]:
        if server_id not in self.servers:
            raise ServerNotFound(server_id=server_id)
        for user in self.servers[server_id]._users:
            if user.user_name == user_name:
                date_imported = datetime.now().strftime("%Y%m%d%H%M%S")
                ssh_public_key_id = (
                    f"{server_id}:{user_name}:public_key:{date_imported}"
                )
                key: UserSshPublicKey = {
                    "ssh_public_key_id": ssh_public_key_id,
                    "ssh_public_key_body": ssh_public_key_body,
                    "date_imported": date_imported,
                }
                user.ssh_public_keys.append(key)
                return server_id, ssh_public_key_id, user_name
        raise UserNotFound(user_name=user_name, server_id=server_id)

    def delete_ssh_public_key(
        self, server_id: str, ssh_public_key_id: str, user_name: str
    ) -> None:
        if server_id not in self.servers:
            raise ServerNotFound(server_id=server_id)
        for i, user in enumerate(self.servers[server_id]._users):
            if user.user_name == user_name:
                for j, key in enumerate(
                    self.servers[server_id]._users[i].ssh_public_keys
                ):
                    if key["ssh_public_key_id"] == ssh_public_key_id:
                        del user.ssh_public_keys[j]
                        return
                raise PublicKeyNotFound(
                    user_name=user_name,
                    server_id=server_id,
                    ssh_public_key_id=ssh_public_key_id,
                )
        raise UserNotFound(user_name=user_name, server_id=server_id)


transfer_backends = BackendDict(TransferBackend, "transfer")
