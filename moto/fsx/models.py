"""FSxBackend class with methods for supported APIs."""

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel


class FSxBackend(BaseBackend):
    """Implementation of FSx APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

    # add methods from here

    def create_file_system(self, client_request_token, file_system_type, storage_capacity, storage_type, subnet_ids, security_group_ids, tags, kms_key_id, windows_configuration, lustre_configuration, ontap_configuration, file_system_type_version, open_zfs_configuration):
        # implement here
        return file_system
    

fsx_backends = BackendDict(FSxBackend, "fsx")
