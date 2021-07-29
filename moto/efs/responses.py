from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse

from .models import efs_backends


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
        tags = self._get_param("Tags")
        resource = self.efs_backend.create_file_system(
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
        return (
            json.dumps(resource.info_json()),
            {"status": 201, "Content-Type": "application/json"},
        )

    def describe_file_systems(self):
        max_items = self._get_int_param("MaxItems", 10)
        marker = self._get_param("Marker")
        creation_token = self._get_param("CreationToken")
        file_system_id = self._get_param("FileSystemId")
        next_marker, file_systems = self.efs_backend.describe_file_systems(
            marker=marker,
            max_items=max_items,
            creation_token=creation_token,
            file_system_id=file_system_id,
        )
        resp_json = {"FileSystems": file_systems}
        if marker:
            resp_json["Marker"] = marker
        if next_marker:
            resp_json["NextMarker"] = next_marker
        return json.dumps(resp_json), {"Content-Type": "application/json"}

    def create_mount_target(self):
        file_system_id = self._get_param("FileSystemId")
        subnet_id = self._get_param("SubnetId")
        ip_address = self._get_param("IpAddress")
        security_groups = self._get_param("SecurityGroups")
        mount_target = self.efs_backend.create_mount_target(
            file_system_id=file_system_id,
            subnet_id=subnet_id,
            ip_address=ip_address,
            security_groups=security_groups,
        )
        return (
            json.dumps(mount_target.info_json()),
            {"Content-Type": "application/json"},
        )

    def describe_mount_targets(self):
        max_items = self._get_int_param("MaxItems", 10)
        marker = self._get_param("Marker")
        file_system_id = self._get_param("FileSystemId")
        mount_target_id = self._get_param("MountTargetId")
        access_point_id = self._get_param("AccessPointId")
        next_marker, mount_targets = self.efs_backend.describe_mount_targets(
            max_items=max_items,
            file_system_id=file_system_id,
            mount_target_id=mount_target_id,
            access_point_id=access_point_id,
            marker=marker,
        )
        resp_json = {"MountTargets": mount_targets}
        if marker:
            resp_json["Marker"] = marker
        if next_marker:
            resp_json["NextMarker"] = next_marker
        return json.dumps(resp_json), {"Content-Type": "application/json"}

    def delete_file_system(self):
        file_system_id = self._get_param("FileSystemId")
        self.efs_backend.delete_file_system(file_system_id=file_system_id,)
        return json.dumps(dict()), {"status": 204, "Content-Type": "application/json"}

    def delete_mount_target(self):
        mount_target_id = self._get_param("MountTargetId")
        self.efs_backend.delete_mount_target(mount_target_id=mount_target_id,)
        return json.dumps(dict()), {"status": 204, "Content-Type": "application/json"}

    def describe_backup_policy(self):
        file_system_id = self._get_param("FileSystemId")
        backup_policy = self.efs_backend.describe_backup_policy(
            file_system_id=file_system_id,
        )
        resp = {"BackupPolicy": backup_policy}
        return json.dumps(resp), {"Content-Type": "application/json"}
