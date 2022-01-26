import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from boto3 import Session
from botocore.client import ClientError
from moto import settings, mock_s3control

# All tests for s3-control cannot be run under the server without a modification of the
# hosts file on your system. This is due to the fact that the URL to the host is in the form of:
# ACCOUNT_ID.s3-control.amazonaws.com <-- That Account ID part is the problem. If you want to
# make use of the moto server, update your hosts file for `THE_ACCOUNT_ID_FOR_MOTO.localhost`
# and this will work fine.

if not settings.TEST_SERVER_MODE:

    @mock_s3control
    def test_get_public_access_block_for_account():
        from moto.s3.models import ACCOUNT_ID

        client = boto3.client("s3control", region_name="us-west-2")

        # With an invalid account ID:
        with pytest.raises(ClientError) as ce:
            client.get_public_access_block(AccountId="111111111111")
        assert ce.value.response["Error"]["Code"] == "AccessDenied"

        # Without one defined:
        with pytest.raises(ClientError) as ce:
            client.get_public_access_block(AccountId=ACCOUNT_ID)
        assert (
            ce.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
        )

        # Put a with an invalid account ID:
        with pytest.raises(ClientError) as ce:
            client.put_public_access_block(
                AccountId="111111111111",
                PublicAccessBlockConfiguration={"BlockPublicAcls": True},
            )
        assert ce.value.response["Error"]["Code"] == "AccessDenied"

        # Put with an invalid PAB:
        with pytest.raises(ClientError) as ce:
            client.put_public_access_block(
                AccountId=ACCOUNT_ID, PublicAccessBlockConfiguration={}
            )
        assert ce.value.response["Error"]["Code"] == "InvalidRequest"
        assert (
            "Must specify at least one configuration."
            in ce.value.response["Error"]["Message"]
        )

        # Correct PAB:
        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        # Get the correct PAB (for all regions):
        for region in Session().get_available_regions("s3control"):
            region_client = boto3.client("s3control", region_name=region)
            assert region_client.get_public_access_block(AccountId=ACCOUNT_ID)[
                "PublicAccessBlockConfiguration"
            ] == {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }

        # Delete with an invalid account ID:
        with pytest.raises(ClientError) as ce:
            client.delete_public_access_block(AccountId="111111111111")
        assert ce.value.response["Error"]["Code"] == "AccessDenied"

        # Delete successfully:
        client.delete_public_access_block(AccountId=ACCOUNT_ID)

        # Confirm that it's deleted:
        with pytest.raises(ClientError) as ce:
            client.get_public_access_block(AccountId=ACCOUNT_ID)
        assert (
            ce.value.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration"
        )
