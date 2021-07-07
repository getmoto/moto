from __future__ import unicode_literals

import string
import time
import random
from copy import deepcopy

from boto3 import Session
from moto.core import BaseBackend, BaseModel, CloudFormationModel, ACCOUNT_ID
from moto.core.utils import underscores_to_camelcase, camelcase_to_underscores
from moto.efs.exceptions import FileSystemAlreadyExists, BadRequest


class FileSystem(CloudFormationModel):
    def __init__(
        self,
        creation_token,
        file_system_id,
        performance_mode="generalPurpose",
        encrypted=False,
        kms_key_id=None,
        throughput_mode="bursting",
        provisioned_throughput_in_mibps=None,
        availability_zone_name=None,
        backup=False,
        lifecycle_policies=None,
        file_system_policy=None,
        tags=None,
    ):
        if availability_zone_name:
            backup = True
        if kms_key_id and not encrypted:
            raise BadRequest('If kms_key_id given, "encrypted" must be True.')

        # Save given parameters
        self.creation_token = creation_token
        self.performance_mode = performance_mode
        self.encrypted = encrypted
        self.kms_key_id = kms_key_id
        self.throughput_mode = throughput_mode
        self.provisioned_throughput_in_mibps = provisioned_throughput_in_mibps
        self.availability_zone_name = availability_zone_name
        self.backup = backup
        self.lifecycle_policies = lifecycle_policies
        self.file_system_policy = file_system_policy

        # Validate tag structure.
        if tags is None:
            self.tags = []
        else:
            if (
                not isinstance(tags, list)
                or not all(isinstance(tag, dict) for tag in tags)
                or not all(set(tag.keys()) == {"Key", "Value"} for tag in tags)
            ):
                raise ValueError("Invalid tags: {}".format(tags))

        # Generate AWS-assigned parameters
        self.file_system_id = file_system_id
        self.file_system_arn = "arn:aws:elasticfilesystem:{region}:{user_id}:file-system/{file_system_id}".format(
            region=None, user_id=None, file_system_id=self.file_system_id
        )
        self.creation_time = time.time()
        self.user_id = ACCOUNT_ID

        # Assign the physical reasource ID, used internally
        self.physical_resource_id = file_system_id

    def info_json(self):
        return {
            underscores_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if not k.startswith("_")
        }

    @staticmethod
    def cloudformation_name_type():
        return

    @staticmethod
    def cloudformation_type():
        return "AWS::EFS::FileSystem"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-efs-filesystem.html
        props = deepcopy(cloudformation_json["Properties"])
        props = {camelcase_to_underscores(k): v for k, v in props.items()}
        if "file_system_tags" in props:
            props["tags"] = props.pop("file_system_tags")
        if "backup_policy" in props:
            if "status" not in props["backup_policy"]:
                raise ValueError("BackupPolicy must be of type BackupPolicy.")
            status = props.pop("backup_policy")["status"]
            if status not in ["ENABLED", "DISABLED"]:
                raise ValueError('Invalid status: "{}".'.format(status))
            props["backup"] = status == "ENABLED"
        if "bypass_policy_lockout_safety_check" in props:
            raise ValueError(
                "BypassPolicyLockoutSafetyCheck not currently "
                "supported by AWS Cloudformation."
            )

        return efs_backends[region_name].create_file_system(resource_name, **props)

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        return

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        return


class EFSBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(EFSBackend, self).__init__()
        self.region_name = region_name
        self.creation_tokens = set()
        self.file_systems_by_id = {}

    def create_file_system(self, creation_token, **params):
        if not creation_token:
            raise ValueError("No creation token given.")
        if creation_token in self.creation_tokens:
            raise FileSystemAlreadyExists(creation_token)

        # Create a new file system ID:
        def make_id():
            fsid = "fs-" + "".join(
                [
                    random.choice(string.ascii_lowercase + string.digits)
                    for _ in range(15)
                ]
            )
            return fsid

        fsid = make_id()
        while fsid in self.file_systems_by_id:
            fsid = make_id()
        self.file_systems_by_id[fsid] = FileSystem(creation_token, fsid, **params)
        self.creation_tokens.add(creation_token)
        return self.file_systems_by_id[fsid]

    def describe_file_systems(self, max_items, creation_token, file_system_id):
        # implement here
        return marker, file_systems
    
    # add methods from here


efs_backends = {}
for region in Session().get_available_regions("efs"):
    efs_backends[region] = EFSBackend()
for region in Session().get_available_regions("efs", partition_name="aws-us-gov"):
    efs_backends[region] = EFSBackend()
for region in Session().get_available_regions("efs", partition_name="aws-cn"):
    efs_backends[region] = EFSBackend()
