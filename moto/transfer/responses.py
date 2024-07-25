"""Handles incoming transfer requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import transfer_backends


class TransferResponse(BaseResponse):
    """Handler for Transfer requests and responses."""

    def __init__(self):
        super().__init__(service_name="transfer")

    @property
    def transfer_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # transfer_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return transfer_backends[self.current_account][self.region]

    # add methods from here

    
    def create_user(self):
        params = self._get_params()
        home_directory = params.get("HomeDirectory")
        home_directory_type = params.get("HomeDirectoryType")
        home_directory_mappings = params.get("HomeDirectoryMappings")
        policy = params.get("Policy")
        posix_profile = params.get("PosixProfile")
        role = params.get("Role")
        server_id = params.get("ServerId")
        ssh_public_key_body = params.get("SshPublicKeyBody")
        tags = params.get("Tags")
        user_name = params.get("UserName")
        server_id, user_name = self.transfer_backend.create_user(
            home_directory=home_directory,
            home_directory_type=home_directory_type,
            home_directory_mappings=home_directory_mappings,
            policy=policy,
            posix_profile=posix_profile,
            role=role,
            server_id=server_id,
            ssh_public_key_body=ssh_public_key_body,
            tags=tags,
            user_name=user_name,
        )
        # TODO: adjust response
        return json.dumps(dict(serverId=server_id, userName=user_name))

    
    def describe_user(self):
        params = self._get_params()
        server_id = params.get("ServerId")
        user_name = params.get("UserName")
        server_id, user = self.transfer_backend.describe_user(
            server_id=server_id,
            user_name=user_name,
        )
        # TODO: adjust response
        return json.dumps(dict(serverId=server_id, user=user))
# add templates from here
    
    def delete_user(self):
        params = self._get_params()
        server_id = params.get("ServerId")
        user_name = params.get("UserName")
        self.transfer_backend.delete_user(
            server_id=server_id,
            user_name=user_name,
        )
        # TODO: adjust response
        return json.dumps(dict())
    
    def import_ssh_public_key(self):
        params = self._get_params()
        server_id = params.get("ServerId")
        ssh_public_key_body = params.get("SshPublicKeyBody")
        user_name = params.get("UserName")
        server_id, ssh_public_key_id, user_name = self.transfer_backend.import_ssh_public_key(
            server_id=server_id,
            ssh_public_key_body=ssh_public_key_body,
            user_name=user_name,
        )
        # TODO: adjust response
        return json.dumps(dict(serverId=server_id, sshPublicKeyId=ssh_public_key_id, userName=user_name))
