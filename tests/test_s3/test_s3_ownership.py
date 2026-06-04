import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME


@mock_aws
def test_create_bucket_with_ownership():
    bucket = "bucket-with-owner"
    ownership = "BucketOwnerPreferred"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket, ObjectOwnership=ownership)

    response = client.get_bucket_ownership_controls(Bucket=bucket)
    assert response["OwnershipControls"]["Rules"][0]["ObjectOwnership"] == ownership


@mock_aws
def test_put_ownership_to_bucket():
    bucket = "bucket-updated-with-owner"
    ownership = "ObjectWriter"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket)

    client.put_bucket_ownership_controls(
        Bucket=bucket, OwnershipControls={"Rules": [{"ObjectOwnership": ownership}]}
    )

    response = client.get_bucket_ownership_controls(Bucket=bucket)
    assert response["OwnershipControls"]["Rules"][0]["ObjectOwnership"] == ownership


@mock_aws
def test_delete_ownership_from_bucket():
    bucket = "bucket-with-owner-removed"
    ownership = "BucketOwnerEnforced"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    client.create_bucket(Bucket=bucket, ObjectOwnership=ownership)

    client.delete_bucket_ownership_controls(Bucket=bucket)

    with pytest.raises(ClientError) as ex:
        client.get_bucket_ownership_controls(Bucket=bucket)
    metadata = ex.value.response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 404
    error = ex.value.response["Error"]
    assert error["Code"] == "OwnershipControlsNotFoundError"
    assert error["Message"] == "The bucket ownership controls were not found"
    assert error["BucketName"] == bucket  # type: ignore
