"""FSxBackend class with methods for supported APIs."""
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from moto.utilities.tagging_service import TaggingService


class FileSystem(BaseModel):
    def __init__(
            self,
            file_system_type: str,
            storage_capacity: int,
            storage_type: str,
            subnet_ids: List[str],
            security_group_ids: List[str],
            tags: Optional[List[Dict[str, str]]],
            kms_key_id: Optional[str],
            windows_configuration: Optional[Dict[str, Any]],
            lustre_configuration: Optional[Dict[str, Any]],
            ontap_configuration: Optional[Dict[str, Any]],
            open_zfs_configuration: Optional[Dict[str, Any]]
    ):
        self.file_system_id = f"fs-moto{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.file_system_type = file_system_type
        self.storage_capacity = storage_capacity
        self.storage_type = storage_type
        self.subnet_ids = subnet_ids
        self.security_group_ids = security_group_ids
        self.tags = tags
        self.kms_key_id = kms_key_id
        self.windows_configuration = windows_configuration
        self.lustre_configuration = lustre_configuration
        self.ontap_configuration = ontap_configuration
        self.open_zfs_configuration = open_zfs_configuration
    

    def to_dict(self) -> Dict[str, Any]:
        dct = {
            "fileSystemId": self.file_system_id,
            "fileSystemType": self.file_system_type,
            "storageCapacity": self.storage_capacity,
            "storageType": self.storage_type,
            "subnetIds": self.subnet_ids,
            "securityGroupIds": self.security_group_ids,
            "tags": self.tags,
            "kmsKeyId": self.kms_key_id,
            "windowsConfiguration": self.windows_configuration,
            "lustreConfiguration": self.lustre_configuration,
            "ontapConfiguration": self.ontap_configuration,
            "openZFSConfiguration": self.open_zfs_configuration,
        }

        return {k: v for k, v in dct.items() if v}

class FSxBackend(BaseBackend):
    """Implementation of FSx APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.file_systems: Dict[str, FileSystem] = {}
        self.tags: TaggingService = TaggingService()

    def create_file_system(
        self,
        client_request_token,
        file_system_type: str,
        storage_capacity: int,
        storage_type: str,
        subnet_ids: List[str],
        security_group_ids: List[str],
        tags: Optional[List[Dict[str, str]]],
        kms_key_id: Optional[str],
        windows_configuration: Optional[Dict[str, Any]],
        lustre_configuration: Optional[Dict[str, Any]],
        ontap_configuration: Optional[Dict[str, Any]],
        file_system_type_version: Optional[str],
        open_zfs_configuration: Optional[Dict[str, Any]]
    ) -> FileSystem:

        file_system = FileSystem(
            file_system_type=file_system_type,
            storage_capacity=storage_capacity,
            storage_type=storage_type,
            subnet_ids=subnet_ids,
            security_group_ids=security_group_ids,
            tags=tags,
            kms_key_id=kms_key_id,
            windows_configuration=windows_configuration,
            ontap_configuration=ontap_configuration,
            open_zfs_configuration=open_zfs_configuration,
            lustre_configuration=lustre_configuration,
        )

        file_system_id = file_system.file_system_id

        self.file_systems[file_system_id] = file_system
        self.tags.tag_resource(file_system_id, tags)

        return file_system
    
    def describe_file_systems(self, file_system_ids, max_results, next_token):
        # implement here
        file_systems = list(self.file_systems.values())
        next_token = None
        return file_systems, next_token
    

fsx_backends = BackendDict(FSxBackend, "fsx")
