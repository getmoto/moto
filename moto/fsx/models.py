"""FSxBackend class with methods for supported APIs."""

import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService

from .exceptions import ResourceNotFoundException
from .utils import FileSystemType

PAGINATION_MODEL = {
    "describe_file_systems": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 2147483647,
        "unique_attribute": "resource_arn",
    }
}


class FileSystem(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
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
        open_zfs_configuration: Optional[Dict[str, Any]],
    ) -> None:
        self.file_system_id = f"fs-{uuid4().hex[:8]}"
        self.file_system_type = file_system_type
        if self.file_system_type not in FileSystemType.list_values():
            raise ValueError(f"Invalid FileSystemType: {self.file_system_type}")
        self.storage_capacity = storage_capacity
        self.storage_type = storage_type
        self.subnet_ids = subnet_ids
        self.security_group_ids = security_group_ids
        self.dns_name = f"{self.file_system_id}.fsx.{region_name}.amazonaws.com"
        self.kms_key_id = kms_key_id
        self.resource_arn = (
            f"arn:aws:fsx:{region_name}:{account_id}:file-system/{self.file_system_id}"
        )
        self.tags = tags or []
        self.windows_configuration = windows_configuration
        self.lustre_configuration = lustre_configuration
        self.ontap_configuration = ontap_configuration
        self.open_zfs_configuration = open_zfs_configuration

    def to_dict(self) -> Dict[str, Any]:
        dct = {
            "FileSystemId": self.file_system_id,
            "FileSystemType": self.file_system_type,
            "StorageCapacity": self.storage_capacity,
            "StorageType": self.storage_type,
            "SubnetIds": self.subnet_ids,
            "SecurityGroupIds": self.security_group_ids,
            "Tags": self.tags,
            "DNSName": self.dns_name,
            "KmsKeyId": self.kms_key_id,
            "ResourceARN": self.resource_arn,
            "WindowsConfiguration": self.windows_configuration,
            "LustreConfiguration": self.lustre_configuration,
            "OntapConfiguration": self.ontap_configuration,
            "OpenZFSConfiguration": self.open_zfs_configuration,
        }
        return {k: v for k, v in dct.items() if v}


class Backup(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        file_system_id: str,
        client_request_token: Optional[str],
        volume_id: Optional[str],
        tags: Optional[List[Dict[str, str]]],
    ) -> None:
        self.backup_id = f"backup-{uuid4().hex[:8]}"
        self.file_system_id = file_system_id
        self.client_request_token = client_request_token or str(uuid4())
        self.tags = tags or []
        self.volume_id = volume_id
        self.resource_arn = (
            f"arn:aws:fsx:{region_name}:{account_id}:backup/{self.backup_id}"
        )
        self.lifecycle = "CREATING"
        self.creation_time = time.time()

    def to_dict(self) -> Dict[str, Any]:
        dct = {
            "BackupId": self.backup_id,
            "FileSystemId": self.file_system_id,
            "VolumeId": self.volume_id,
            "Lifecycle": self.lifecycle,
            "CreationTime": self.creation_time,
            "Tags": self.tags,
            "ResourceARN": self.resource_arn,
            "ClientRequestToken": self.client_request_token,
        }
        return {k: v for k, v in dct.items() if v is not None}


class FSxBackend(BaseBackend):
    """Implementation of FSx APIs."""

    def __init__(self, region_name: str, account_id: str) -> None:
        super().__init__(region_name, account_id)
        self.file_systems: Dict[str, FileSystem] = {}
        self.backups: Dict[str, Backup] = {}
        self.tagger = TaggingService()

    def create_file_system(
        self,
        client_request_token: str,
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
        open_zfs_configuration: Optional[Dict[str, Any]],
    ) -> FileSystem:
        file_system = FileSystem(
            account_id=self.account_id,
            region_name=self.region_name,
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
        if tags:
            self.tag_resource(resource_arn=file_system.resource_arn, tags=tags)
        return file_system

    @paginate(pagination_model=PAGINATION_MODEL)
    def describe_file_systems(self, file_system_ids: List[str]) -> List[FileSystem]:
        file_systems = []
        if not file_system_ids:
            file_systems = list(self.file_systems.values())
        else:
            for id in file_system_ids:
                if id in self.file_systems:
                    file_systems.append(self.file_systems[id])
        return file_systems

    def delete_file_system(
        self,
        file_system_id: str,
        client_request_token: str,
        windows_configuration: Optional[Dict[str, Any]],
        lustre_configuration: Optional[Dict[str, Any]],
        open_zfs_configuration: Optional[Dict[str, Any]],
    ) -> Tuple[
        str,
        str,
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
        Optional[Dict[str, Any]],
    ]:
        response_template = {"FinalBackUpId": "", "FinalBackUpTags": []}

        file_system_type = self.file_systems[file_system_id].file_system_type

        lifecycle = "DELETING"
        self.file_systems.pop(file_system_id)

        windows_response = None
        lustre_response = None
        open_zfs_response = None

        if file_system_type == "WINDOWS":
            windows_response = response_template
        elif file_system_type == "LUSTRE":
            lustre_response = response_template
        elif file_system_type == "OPEN_ZFS":
            open_zfs_response = response_template

        return (
            file_system_id,
            lifecycle,
            windows_response,
            lustre_response,
            open_zfs_response,
        )

    def create_backup(
        self,
        file_system_id: str,
        client_request_token: Optional[str],
        volume_id: Optional[str],
        tags: Optional[List[Dict[str, str]]],
    ) -> Backup:
        backup = Backup(
            account_id=self.account_id,
            region_name=self.region_name,
            file_system_id=file_system_id,
            client_request_token=client_request_token,
            volume_id=volume_id,
            tags=tags,
        )
        if file_system_id not in self.file_systems:
            raise ResourceNotFoundException(
                msg=f"FSx resource, {file_system_id} does not exist"
            )
        self.backups[backup.backup_id] = backup
        if tags:
            self.tag_resource(resource_arn=backup.resource_arn, tags=tags)
        return backup

    def delete_backup(
        self, backup_id: str, client_request_token: Optional[str]
    ) -> Dict[str, Any]:
        if backup_id not in self.backups:
            raise ResourceNotFoundException(
                msg=f"FSx resource, {backup_id} does not exist"
            )
        self.backups.pop(backup_id)

        return {"BackupId": backup_id, "Lifecycle": "DELETED"}

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def list_tags_for_resource(self, resource_arn: str) -> Optional[Dict[str, Any]]:
        """
        Pagination is not yet implemented
        """
        if self.tagger.has_tags(resource_arn):
            return self.tagger.list_tags_for_resource(resource_arn)
        return None


fsx_backends = BackendDict(FSxBackend, "fsx")
