from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_encryption_on_new_bucket_fails():
    conn = boto3.client("s3", region_name="us-east-1")
    conn.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as exc:
        conn.get_bucket_encryption(Bucket="mybucket")
    err = exc.value.response["Error"]
    assert err["Code"] == "ServerSideEncryptionConfigurationNotFoundError"
    assert err["Message"] == "The server side encryption configuration was not found"
    assert err["BucketName"] == "mybucket"


@mock_aws
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
    assert resp["ServerSideEncryptionConfiguration"] == return_config


@mock_aws
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
    assert err["Code"] == "ServerSideEncryptionConfigurationNotFoundError"


@mock_aws
def test_encryption_status_on_new_objects():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key="file.txt")
    # verify encryption status on object itself
    res = s3_client.get_object(Bucket=bucket_name, Key="file.txt")
    assert "ServerSideEncryption" not in res
    # enable encryption
    sse_config = {
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }
    s3_client.put_bucket_encryption(
        Bucket=bucket_name, ServerSideEncryptionConfiguration=sse_config
    )
    # verify encryption status on existing object hasn't changed
    res = s3_client.get_object(Bucket=bucket_name, Key="file.txt")
    assert "ServerSideEncryption" not in res
    # create object2
    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key="file2.txt")
    # verify encryption status on object2
    res = s3_client.get_object(Bucket=bucket_name, Key="file2.txt")
    assert res["ServerSideEncryption"] == "AES256"


@mock_aws
def test_encryption_status_on_copied_objects():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_object(Bucket=bucket_name, Body=b"test", Key="file.txt")
    # enable encryption
    sse_config = {
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }
    s3_client.put_bucket_encryption(
        Bucket=bucket_name, ServerSideEncryptionConfiguration=sse_config
    )
    # copy object
    s3_client.copy_object(
        CopySource=f"{bucket_name}/file.txt", Bucket=bucket_name, Key="file2.txt"
    )
    # verify encryption status on object1 hasn't changed
    res = s3_client.get_object(Bucket=bucket_name, Key="file.txt")
    assert "ServerSideEncryption" not in res
    # verify encryption status on object2 does have encryption
    res = s3_client.get_object(Bucket=bucket_name, Key="file2.txt")
    assert res["ServerSideEncryption"] == "AES256"


@mock_aws
def test_encryption_bucket_key_for_aes_not_returned():
    bucket_name = str(uuid4())
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket=bucket_name)
    # enable encryption
    sse_config = {
        "Rules": [
            {
                "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                "BucketKeyEnabled": False,
            }
        ]
    }
    s3_client.put_bucket_encryption(
        Bucket=bucket_name, ServerSideEncryptionConfiguration=sse_config
    )
    res = s3_client.put_object(Bucket=bucket_name, Body=b"test", Key="file.txt")
    assert "BucketKeyEnabled" not in res
