import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_s3


@mock_s3
def test_encryption_on_new_bucket_fails():
    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as exc:
        conn.get_bucket_encryption(Bucket="mybucket")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ServerSideEncryptionConfigurationNotFoundError")
    err["Message"].should.equal(
        "The server side encryption configuration was not found"
    )
    err["BucketName"].should.equal("mybucket")


@mock_s3
def test_put_and_get_encryption():
    # Create Bucket so that test can run
    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="mybucket")

    sse_config = {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "12345678",
                }
            }
        ]
    }

    conn.put_bucket_encryption(
        Bucket="mybucket", ServerSideEncryptionConfiguration=sse_config
    )

    resp = conn.get_bucket_encryption(Bucket="mybucket")
    assert "ServerSideEncryptionConfiguration" in resp
    return_config = sse_config.copy()
    return_config["Rules"][0]["BucketKeyEnabled"] = False
    assert resp["ServerSideEncryptionConfiguration"].should.equal(return_config)


@mock_s3
def test_delete_and_get_encryption():
    # Create Bucket so that test can run
    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="mybucket")

    sse_config = {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "aws:kms",
                    "KMSMasterKeyID": "12345678",
                }
            }
        ]
    }

    conn.put_bucket_encryption(
        Bucket="mybucket", ServerSideEncryptionConfiguration=sse_config
    )

    conn.delete_bucket_encryption(Bucket="mybucket")
    # GET now fails, after deleting it, as it no longer exists
    with pytest.raises(ClientError) as exc:
        conn.get_bucket_encryption(Bucket="mybucket")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ServerSideEncryptionConfigurationNotFoundError")
