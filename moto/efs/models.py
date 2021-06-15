from __future__ import unicode_literals

import string
import time
import random

from boto3 import Session
from moto.core import BaseBackend, BaseModel, CloudFormationModel
from moto.core.utils import underscores_to_camelcase
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
        tags=None,
    ):
        if availability_zone_name:
            backup = True
        if kms_key_id and not encrypted:
            raise BadRequest('If kms_key_id given, "ecnrypted" must be True.')

        # Save given parameters
        self.creation_token = creation_token
        self.performance_mode = performance_mode
        self.encrypted = encrypted
        self.kms_key_id = kms_key_id
        self.throughput_mode = throughput_mode
        self.provisioned_throughput_in_mibps = provisioned_throughput_in_mibps
        self.availability_zone_name = availability_zone_name
        self.backup = backup
        if tags is None:
            self.tags = []

        # Generate AWS-assigned parameters

        self.file_system_id = file_system_id
        self.file_system_arn = "arn:aws:elasticfilesystem:{region}:{user_id}:file-system/{file_system_id}".format(
            region=None, user_id=None, file_system_id=self.file_system_id
        )
        self.creation_time = time.time()
        self.user_id = NotImplemented  # TODO

    def info_json(self):
        return {
            underscores_to_camelcase(k): v
            for k, v in self.__dict__.items()
            if not k.startswith("_")
        }

    @staticmethod
    def cloudformation_name_type():
        return "FileSystemId"

    @staticmethod
    def cloudformation_type():
        return "AWS::EFS::FileSystem"

    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        pass

    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        pass

    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        pass


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
        return self.file_systems_by_id[fsid].info_json()

    # add methods from here


efs_backends = {}
for region in Session().get_available_regions("efs"):
    efs_backends[region] = EFSBackend()
for region in Session().get_available_regions("efs", partition_name="aws-us-gov"):
    efs_backends[region] = EFSBackend()
for region in Session().get_available_regions("efs", partition_name="aws-cn"):
    efs_backends[region] = EFSBackend()
