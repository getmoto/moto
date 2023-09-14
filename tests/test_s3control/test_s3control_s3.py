"""Test that using both s3 and s3control do not interfere"""
import boto3

from moto import mock_s3, mock_s3control, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


if not settings.TEST_SERVER_MODE:

    @mock_s3
    @mock_s3control
    def test_pab_are_kept_separate():
        client = boto3.client("s3control", region_name="us-east-1")
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="bucket")

        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        s3_client.put_public_access_block(
            Bucket="bucket",
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": False,
            },
        )

        pab_from_control = client.get_public_access_block(AccountId=ACCOUNT_ID)
        assert pab_from_control["PublicAccessBlockConfiguration"] == {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }

        pab_from_s3 = s3_client.get_public_access_block(Bucket="bucket")
        assert pab_from_s3["PublicAccessBlockConfiguration"] == {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": False,
        }

    @mock_s3control
    @mock_s3
    def test_pab_are_kept_separate_with_inverse_mocks():
        client = boto3.client("s3control", region_name="us-east-1")
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket="bucket")

        client.put_public_access_block(
            AccountId=ACCOUNT_ID,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )

        s3_client.put_public_access_block(
            Bucket="bucket",
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": False,
            },
        )

        pab_from_control = client.get_public_access_block(AccountId=ACCOUNT_ID)
        assert pab_from_control["PublicAccessBlockConfiguration"] == {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        }

        pab_from_s3 = s3_client.get_public_access_block(Bucket="bucket")
        assert pab_from_s3["PublicAccessBlockConfiguration"] == {
            "BlockPublicAcls": True,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": False,
        }
