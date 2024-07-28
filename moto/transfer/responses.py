"""Handles incoming transfer requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import TransferBackend, transfer_backends


class TransferResponse(BaseResponse):
    """Handler for Transfer requests and responses."""

    def __init__(self):
        super().__init__(service_name="transfer")

    @property
    def transfer_backend(self) -> TransferBackend:
        return transfer_backends[self.current_account][self.region]
    
    def create_user(self):
        params = json.loads(self.body)
        server_id, user_name = self.transfer_backend.create_user(
            home_directory=params.get("HomeDirectory"),
            home_directory_type=params.get("HomeDirectoryType"),
            home_directory_mappings=params.get("HomeDirectoryMappings"),
            policy=params.get("Policy"),
            posix_profile=params.get("PosixProfile"),
            role=params.get("Role"),
            server_id=params.get("ServerId"),
            ssh_public_key_body=params.get("SshPublicKeyBody"),
            tags=params.get("Tags"),
            user_name=params.get("UserName"),
        )
        return json.dumps(dict(serverId=server_id, userName=user_name))

    
    def describe_user(self) -> str:
        params = json.loads(self.body)
        server_id, user = self.transfer_backend.describe_user(
            server_id=params.get("ServerId"),
            user_name=params.get("UserName"),
        )
        return json.dumps(dict(serverId=server_id, user=user.to_dict()))
    
    def delete_user(self):
        params = self._get_params()
        self.transfer_backend.delete_user(
            server_id=params.get("ServerId"),
            user_name=params.get("UserName"),
        )
        return json.dumps(dict())
    
    def import_ssh_public_key(self):
        params = self._get_params()
        server_id, ssh_public_key_id, user_name = self.transfer_backend.import_ssh_public_key(
            server_id=params.get("ServerId"),
            ssh_public_key_body=params.get("SshPublicKeyBody"),
            user_name=params.get("UserName"),
        )
        return json.dumps(dict(serverId=server_id, sshPublicKeyId=ssh_public_key_id, userName=user_name))
    
    def delete_ssh_public_key(self):
        params = self._get_params()
        self.transfer_backend.delete_ssh_public_key(
            server_id=params.get("ServerId"),
            ssh_public_key_id=params.get("SshPublicKeyId"),
            user_name=params.get("UserName"),
        )
        return json.dumps(dict())
