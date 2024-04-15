import boto3

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

REGION = "us-east-1"


if not settings.TEST_SERVER_MODE:

    @mock_aws
    def test_pab_are_kept_separate():
        client = boto3.client("s3control", region_name=REGION)
        s3_client = boto3.client("s3", region_name=REGION)
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

    @mock_aws
    def test_pab_are_kept_separate_with_inverse_mocks():
        client = boto3.client("s3control", region_name=REGION)
        s3_client = boto3.client("s3", region_name=REGION)
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

    @mock_aws
    def test_access_point_read_write():
        # Setup
        bucket = "test-bucket"
        ap_client = boto3.client("s3control", region_name=REGION)
        s3_client = boto3.client("s3", region_name=REGION)
        s3_client.create_bucket(Bucket=bucket)

        read_ap = ap_client.create_access_point(
            AccountId=ACCOUNT_ID, Name="read-ap", Bucket=bucket
        )
        write_ap = ap_client.create_access_point(
            AccountId=ACCOUNT_ID, Name="write-ap", Bucket=bucket
        )

        content = b"This is test content"
        key = "test/object.txt"

        # Execute
        s3_client.put_object(
            Bucket=write_ap["AccessPointArn"],
            Key=key,
            Body=content,
            ContentType="text/plain",
        )

        # Verify
        assert (
            s3_client.get_object(Bucket=read_ap["AccessPointArn"], Key=key)[
                "Body"
            ].read()
            == content
        )
        assert s3_client.get_object(Bucket=bucket, Key=key)["Body"].read() == content
