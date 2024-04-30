"""Handles incoming fsx requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import fsx_backends


class FSxResponse(BaseResponse):
    """Handler for FSx requests and responses."""

    def __init__(self):
        super().__init__(service_name="fsx")

    @property
    def fsx_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # fsx_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return fsx_backends[self.current_account][self.region]

    def create_file_system(self):
        params = self._get_params()
        client_request_token = params.get("ClientRequestToken")
        file_system_type = params.get("FileSystemType")
        storage_capacity = params.get("StorageCapacity")
        storage_type = params.get("StorageType")
        subnet_ids = params.get("SubnetIds")
        security_group_ids = params.get("SecurityGroupIds")
        tags = params.get("Tags")
        kms_key_id = params.get("KmsKeyId")
        windows_configuration = params.get("WindowsConfiguration")
        lustre_configuration = params.get("LustreConfiguration")
        ontap_configuration = params.get("OntapConfiguration")
        file_system_type_version = params.get("FileSystemTypeVersion")
        open_zfs_configuration = params.get("OpenZFSConfiguration")
        file_system = self.fsx_backend.create_file_system(
            client_request_token=client_request_token,
            file_system_type=file_system_type,
            storage_capacity=storage_capacity,
            storage_type=storage_type,
            subnet_ids=subnet_ids,
            security_group_ids=security_group_ids,
            tags=tags,
            kms_key_id=kms_key_id,
            windows_configuration=windows_configuration,
            lustre_configuration=lustre_configuration,
            ontap_configuration=ontap_configuration,
            file_system_type_version=file_system_type_version,
            open_zfs_configuration=open_zfs_configuration,
        )

        return json.dumps(dict(fileSystem=file_system.to_dict()))

    
    def describe_file_systems(self):
        params = self._get_params()
        file_system_ids = params.get("FileSystemIds")
        max_results = params.get("MaxResults")
        next_token = params.get("NextToken")
        file_systems, next_token = self.fsx_backend.describe_file_systems(
            file_system_ids=file_system_ids,
            max_results=max_results,
            next_token=next_token,
        )

        return json.dumps(dict(fileSystem=file_systems))

# add templates from here
