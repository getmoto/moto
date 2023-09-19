import os
from unittest import SkipTest, mock

import boto3
from botocore.client import ClientError
import pytest

from moto import settings, mock_s3
from moto.s3.responses import DEFAULT_REGION_NAME


@mock_s3
def test_cross_account_region_access():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Multi-accounts env config only works serverside")

    client1 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client2 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    account2 = "222222222222"
    bucket_name = "cross-account-bucket"
    key = "test-key"

    # Create a bucket in the default account
    client1.create_bucket(Bucket=bucket_name)
    client1.put_object(Bucket=bucket_name, Key=key, Body=b"data")

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account2}):
        # Ensure the bucket can be retrieved from another account
        response = client2.list_objects(Bucket=bucket_name)
        assert len(response["Contents"]) == 1
        assert response["Contents"][0]["Key"] == key

        assert client2.get_object(Bucket=bucket_name, Key=key)

        assert client2.put_object(Bucket=bucket_name, Key=key, Body=b"kaytranada")

        # Ensure bucket namespace is shared across accounts
        with pytest.raises(ClientError) as exc:
            client2.create_bucket(Bucket=bucket_name)
        assert exc.value.response["Error"]["Code"] == "BucketAlreadyExists"
        assert exc.value.response["Error"]["Message"] == (
            "The requested bucket name is not available. The bucket "
            "namespace is shared by all users of the system. Please "
            "select a different name and try again"
        )

        with mock.patch.dict(
            os.environ, {"MOTO_S3_ALLOW_CROSSACCOUNT_ACCESS": "false"}
        ):
            with pytest.raises(ClientError) as ex:
                client2.list_objects(Bucket=bucket_name)
            assert ex.value.response["Error"]["Code"] == "AccessDenied"
            assert ex.value.response["Error"]["Message"] == "Access Denied"

    # Ensure bucket name can be reused if it is deleted
    client1.delete_object(Bucket=bucket_name, Key=key)
    client1.delete_bucket(Bucket=bucket_name)
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": account2}):
        assert client2.create_bucket(Bucket=bucket_name)
