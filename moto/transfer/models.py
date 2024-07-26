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
        # {Server ID: [User Names]}
        self.servers: Dict[str, List[str]] = {}
        # {User Name: User}
        self.users: Dict[str, User] = {}

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
        if server_id not in self.servers:
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
        self.servers[server_id].append(user.UserName)
        self.users[user.UserName] = user
        return server_id, user_name
    
    def describe_user(self, server_id: str, user_name: str) -> Tuple[str, User]:
        if user_name not in self.users:
            raise UserNotFound(user_name=user_name)
        return server_id, self.users[user_name]
    
    def delete_user(
        self, 
        server_id: str, 
        user_name: str
    ) -> None:
        if user_name not in self.users:
            raise UserNotFound(user_name=user_name)
        if server_id not in self.servers:
            raise ServerNotFound(server_id=server_id)
        if user_name not in self.servers[server_id]:
            raise ServerNotAssociatedWithUser(server_id=server_id, user_name=user_name)
        del self.users[user_name]
        self.servers[server_id].remove(user_name)
        return 
    
    def import_ssh_public_key(
        self, 
        server_id: str, 
        ssh_public_key_body: str, 
        user_name: str
    ) -> Tuple[str, str, str]:
        ssh_public_key_id = "TODO"
        return server_id, ssh_public_key_id, user_name
    

transfer_backends = BackendDict(TransferBackend, "transfer")
