"""S3ControlBackend class with methods for supported APIs."""
from collections import defaultdict

from boto3 import Session

from moto.core import BaseBackend, BaseModel
from moto.s3control.exceptions import (
    NoSuchPublicAccessBlockConfiguration,
    WrongPublicAccessBlockAccountIdError,
)


class PublicAccessBlock(BaseModel):
    def __init__(
        self,
        block_public_acls=False,
        ignore_public_acls=False,
        block_public_policy=False,
        restrict_public_buckets=False,
    ):
        # The boto XML appears to expect these values to exist as lowercase strings...
        self.block_public_acls = block_public_acls or "false"
        self.ignore_public_acls = ignore_public_acls or "false"
        self.block_public_policy = block_public_policy or "false"
        self.restrict_public_buckets = restrict_public_buckets or "false"

    def to_config_dict(self):
        # Need to make the string values booleans for Config:
        return {
            "blockPublicAcls": convert_str_to_bool(self.block_public_acls),
            "ignorePublicAcls": convert_str_to_bool(self.ignore_public_acls),
            "blockPublicPolicy": convert_str_to_bool(self.block_public_policy),
            "restrictPublicBuckets": convert_str_to_bool(self.restrict_public_buckets),
        }


def convert_str_to_bool(item):
    """Converts a boolean string to a boolean value"""
    if isinstance(item, str):
        return item.lower() == "true"

    return False


class S3ControlBackend(BaseBackend):
    """Implementation of S3Control APIs."""

    def __init__(self, region_name):
        self.initialized = defaultdict()
        self.region_name = region_name
        self.public_access_block_configuration = defaultdict()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def get_public_access_block(account_id):
        if account_id not in s3control_backends:
            raise WrongPublicAccessBlockAccountIdError()
        s3control_backend = s3control_backends[account_id]
        if not s3control_backend.initialized or s3control_backend is None:
            raise NoSuchPublicAccessBlockConfiguration()
        return s3control_backend.public_access_block_configuration

    def put_public_access_block(self, account_id, public_access_block_configuration):
        if account_id not in s3control_backends:
            s3control_backends[account_id] = S3ControlBackend(self.region_name)
            s3control_backend = s3control_backends[account_id]
        else:
            s3control_backend = s3control_backends[account_id]
        s3control_backend.initialized = True
        s3control_backend.public_access_block_configuration = PublicAccessBlock(
            public_access_block_configuration.get("BlockPublicAcls"),
            public_access_block_configuration.get("IgnorePublicAcls"),
            public_access_block_configuration.get("BlockPublicPolicy"),
            public_access_block_configuration.get("RestrictPublicBuckets"),
        )

    @staticmethod
    def delete_public_access_block(account_id):
        s3control_backend = s3control_backends[account_id]
        s3control_backend.initialized = False


s3control_backends = {}
for available_region in Session().get_available_regions("s3control"):
    s3control_backends[available_region] = S3ControlBackend(available_region)
for available_region in Session().get_available_regions(
    "s3control", partition_name="aws-us-gov"
):
    s3control_backends[available_region] = S3ControlBackend(available_region)
for available_region in Session().get_available_regions(
    "s3control", partition_name="aws-cn"
):
    s3control_backends[available_region] = S3ControlBackend(available_region)
