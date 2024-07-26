"""TransferBackend class with methods for supported APIs."""

from typing import Dict, Optional, Tuple
from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from moto.transfer.exceptions import ServerNotAssociatedWithUser, ServerNotFound, UserNotFound

from .types import *

class TransferBackend(BaseBackend):
    """Implementation of Transfer APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.server_users: Dict[str, List[User]] = {}

    def create_user(
        self, 
        home_directory: Optional[str], 
        home_directory_type: Optional[HomeDirectoryType], 
        home_directory_mappings: List[HomeDirectoryMapping], 
        policy: Optional[str], 
        posix_profile: Optional[PosixProfile], 
        role: str, 
        server_id: str, 
        ssh_public_key_body: Optional[str], 
        tags: Optional[List[Dict[str,str]]], 
        user_name: str
    ) -> Tuple[str, str]:
        if server_id not in self.server_users:
            raise ServerNotFound(server_id=server_id)
        ssh_public_keys: List[SshPublicKey] = [
            {
                'DateImported': datetime.now().strftime('%Y%m%d%H%M%S'),
                'SshPublicKeyBody': ssh_public_key_body,
                'SshPublicKeyId': "mock_id" # TODO figure this out
            }
        ]
        user = User(
            HomeDirectory=home_directory,
            HomeDirectoryType=home_directory_type,
            Policy=policy,
            PosixProfile=posix_profile,
            Role=role,
            SshPublicKeys=ssh_public_keys,
            Tags=tags,
            UserName=user_name
        )
        self.server_users[server_id].append(user)
        return server_id, user_name
    
    def describe_user(self, server_id: str, user_name: str) -> Tuple[str, User]:
        if server_id not in self.server_users:
            raise ServerNotFound(server_id=server_id)
        for user in self.server_users[server_id]:
            if user.name == user_name:
                return server_id, user
        raise UserNotFound(user_name=user_name, server_id=server_id)
    
    def delete_user(
        self, 
        server_id: str, 
        user_name: str
    ) -> None:
        if server_id not in self.server_users:
            raise ServerNotFound(server_id=server_id)
        for i, user in enumerate(self.server_users[server_id]):
            if user.UserName == user_name:
                del self.server_users[server_id][i]
                return
        raise UserNotFound(server_id=server_id, user_name=user_name)
    
    def import_ssh_public_key(
        self, 
        server_id: str, 
        ssh_public_key_body: str, 
        user_name: str
    ) -> Tuple[str, str, str]:
        ssh_public_key_id = "TODO"
        if server_id not in self.server_users:
            raise ServerNotFound(server_id=server_id)
        for user in self.server_users[server_id]:
            if user.name == user_name:
                # TODO create and add ssh key        
                return server_id, ssh_public_key_id, user_name
        # TODO raise error
    
    def delete_ssh_public_key(
        self,
        server_id: str, 
        ssh_public_key_id: str, 
        user_name: str
    ) -> None:
        # implement here
        return 
    

transfer_backends = BackendDict(TransferBackend, "transfer")
