from moto.core import ACCOUNT_ID, BaseBackend
from moto.s3.exceptions import (
    WrongPublicAccessBlockAccountIdError,
    NoSuchPublicAccessBlockConfiguration,
    InvalidPublicAccessBlockConfiguration,
)
from moto.s3.models import PublicAccessBlock


class S3ControlBackend(BaseBackend):
    """
    S3-Control cannot be accessed via the MotoServer without a modification of the hosts file on your system.
    This is due to the fact that the URL to the host is in the form of:
    ACCOUNT_ID.s3-control.amazonaws.com

    That Account ID part is the problem. If you want to make use of the moto server, update your hosts file for `THE_ACCOUNT_ID_FOR_MOTO.localhost` and this will work fine.
    """

    def __init__(self, region_name=None):
        self.region_name = region_name
        self.public_access_block = None

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def get_public_access_block(self, account_id):
        # The account ID should equal the account id that is set for Moto:
        if account_id != ACCOUNT_ID:
            raise WrongPublicAccessBlockAccountIdError()

        if not self.public_access_block:
            raise NoSuchPublicAccessBlockConfiguration()

        return self.public_access_block

    def delete_public_access_block(self, account_id):
        # The account ID should equal the account id that is set for Moto:
        if account_id != ACCOUNT_ID:
            raise WrongPublicAccessBlockAccountIdError()

        self.public_access_block = None

    def put_public_access_block(self, account_id, pub_block_config):
        # The account ID should equal the account id that is set for Moto:
        if account_id != ACCOUNT_ID:
            raise WrongPublicAccessBlockAccountIdError()

        if not pub_block_config:
            raise InvalidPublicAccessBlockConfiguration()

        self.public_access_block = PublicAccessBlock(
            pub_block_config.get("BlockPublicAcls"),
            pub_block_config.get("IgnorePublicAcls"),
            pub_block_config.get("BlockPublicPolicy"),
            pub_block_config.get("RestrictPublicBuckets"),
        )


s3control_backend = S3ControlBackend()
