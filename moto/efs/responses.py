from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import efs_backends
import json


class EFSResponse(BaseResponse):
    SERVICE_NAME = "efs"

    @property
    def efs_backend(self):
        return efs_backends[self.region]

    def create_file_system(self):
        creation_token = self._get_param("CreationToken")
        performance_mode = self._get_param("PerformanceMode")
        encrypted = self._get_param("Encrypted")
        kms_key_id = self._get_param("KmsKeyId")
        throughput_mode = self._get_param("ThroughputMode")
        provisioned_throughput_in_mibps = self._get_param(
            "ProvisionedThroughputInMibps"
        )
        availability_zone_name = self._get_param("AvailabilityZoneName")
        backup = self._get_param("Backup")
        tags = self._get_list_prefix("Tags.member")
        info_json = self.efs_backend.create_file_system(
            creation_token=creation_token,
            performance_mode=performance_mode,
            encrypted=encrypted,
            kms_key_id=kms_key_id,
            throughput_mode=throughput_mode,
            provisioned_throughput_in_mibps=provisioned_throughput_in_mibps,
            availability_zone_name=availability_zone_name,
            backup=backup,
            tags=tags,
        )
        return json.dumps(info_json)

    # add methods from here


# add templates from here
