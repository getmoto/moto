"""FSxBackend class with methods for supported APIs."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from moto.core.base_backend import BackendDict, BaseBackend
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
        open_zfs_configuration: Optional[Dict[str, Any]],
    ):
        self.file_system_id = f"fs-moto{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.file_system_type = file_system_type
        self.storage_capacity = storage_capacity
        self.storage_type = storage_type
        self.subnet_ids = subnet_ids
        self.security_group_ids = security_group_ids
        self.dns_name = f"{self.file_system_id}.fsx.region-name.amazonaws.com"
        self.kms_key_id = kms_key_id
        self.resource_arn = (
            f"arn:aws:fsx:region-name:account-id:file-system/{self.file_system_id}"
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


class FSxBackend(BaseBackend):
    """Implementation of FSx APIs."""

    def __init__(self, region_name, account_id) -> None:
        super().__init__(region_name, account_id)
        self.file_systems: Dict[str, FileSystem] = {}
        self.tagger: TaggingService = TaggingService()

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
        open_zfs_configuration: Optional[Dict[str, Any]],
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
        self.tagger.tag_resource(file_system.resource_arn, tags)
        return file_system

    def describe_file_systems(self, file_system_ids, max_results, next_token) -> Tuple[List[Dict],str]:
        # implement here
        file_systems_fetched = list(self.file_systems.values())
        file_systems = []
        for file_system in file_systems_fetched:
            file_systems.append(file_system.to_dict())
        next_token = None
        return file_systems, next_token

    def delete_file_system(
        self,
        file_system_id,
        client_request_token,
        windows_configuration,
        lustre_configuration,
        open_zfs_configuration,
    ) -> Tuple[str, str, Dict, Dict, Dict]:
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

    def tag_resource(self, resource_arn, tags) -> None:
        resource = self._get_resource_from_arn(resource_arn)
        resource.tags.extend(tags)


    def _get_resource_from_arn(self, arn: str) -> Any:
        target_resource, target_name = arn.split(":")[-1].split("/")
        try:
            resource = self.file_systems.get(target_name)  # type: ignore
        except KeyError:
            message = f"Could not find {target_resource} with name {target_name}"
            raise ValueError(message)
        return resource


fsx_backends = BackendDict(FSxBackend, "fsx")
