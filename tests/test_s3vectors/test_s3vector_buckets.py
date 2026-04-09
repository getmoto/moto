"""Unit tests for s3vectors-supported APIs."""

from uuid import uuid4

import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError

from tests import aws_verified
from tests.test_s3vectors import s3vectors_aws_verified

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_and_get_vector_bucket(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    get_by_name = client.get_vector_bucket(vectorBucketName=bucket_name)["vectorBucket"]
    bucket_arn = get_by_name["vectorBucketArn"]

    assert get_by_name["vectorBucketName"] == bucket_name
    assert (
        bucket_arn == f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}"
    )
    assert get_by_name["encryptionConfiguration"] == {"sseType": "AES256"}

    get_by_arn = client.get_vector_bucket(vectorBucketArn=bucket_arn)["vectorBucket"]
    assert get_by_arn["vectorBucketName"] == bucket_name
    assert get_by_arn["vectorBucketArn"] == bucket_arn
    assert get_by_arn["encryptionConfiguration"] == {"sseType": "AES256"}


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_and_list_vector_buckets(bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    bucket_list = client.list_vector_buckets()["vectorBuckets"]
    bucket_names = [b["vectorBucketName"] for b in bucket_list]
    assert bucket_name in bucket_names

    client.delete_vector_bucket(vectorBucketName=bucket_name)

    bucket_list = client.list_vector_buckets()["vectorBuckets"]
    bucket_names = [b["vectorBucketName"] for b in bucket_list]
    assert bucket_name not in bucket_names


@aws_verified
@pytest.mark.aws_verified
def test_list_vector_buckets_by_prefix():
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_names = [
        f"prefix1-{str(uuid4())}",
        f"prefix1-{str(uuid4())}",
        f"prefix1-{str(uuid4())}",
        f"prefix2-{str(uuid4())}",
        f"prefix2-{str(uuid4())}",
    ]
    for bucket_name in bucket_names:
        client.create_vector_bucket(vectorBucketName=bucket_name)

    try:
        bucket_list = client.list_vector_buckets(prefix="prefix1")["vectorBuckets"]
        assert len(bucket_list) == 3

        bucket_list = client.list_vector_buckets(prefix="prefix2")["vectorBuckets"]
        assert len(bucket_list) == 2

        bucket_list = client.list_vector_buckets(prefix="prefix3")["vectorBuckets"]
        assert len(bucket_list) == 0
    finally:
        for bucket_name in bucket_names:
            client.delete_vector_bucket(vectorBucketName=bucket_name)


@aws_verified
@pytest.mark.aws_verified
def test_get_unknown_vector_bucket():
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.get_vector_bucket(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified vector bucket could not be found"


@aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "bucket_name",
    [
        "sh",
        "x" * 64,
    ],
)
def test_create_vector_bucket_with_invalid_length(bucket_name):
    # Disable param validation - otherwise boto3 already validates minimum length, and we want to check what AWS says
    config = Config(parameter_validation=False)
    client = boto3.client("s3vectors", region_name="us-east-1", config=config)

    with pytest.raises(ClientError) as exc:
        client.create_vector_bucket(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == f"1 validation error detected. Value with length {len(bucket_name)} at '/vectorBucketName' failed to satisfy constraint: Member must have length between 3 and 63, inclusive"
    )


@aws_verified
@pytest.mark.aws_verified
@pytest.mark.parametrize(
    "bucket_name",
    [
        "with_under_score",
        "special&char",
    ],
)
def test_create_vector_bucket_with_invalid_chars(bucket_name):
    client = boto3.client("s3vectors", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_vector_bucket(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert err["Message"] == "Invalid vector bucket name"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_vector_bucket_twice(bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    # Second creation will fail
    with pytest.raises(ClientError) as exc:
        client.create_vector_bucket(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert err["Message"] == "A vector bucket with the specified name already exists"


@aws_verified
@pytest.mark.aws_verified
def test_delete_unknown_vector_bucket():
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.delete_vector_bucket(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified vector bucket could not be found"
