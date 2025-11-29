"""Unit tests for s3vectors-supported APIs."""

from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from tests import aws_verified
from tests.test_s3vectors import s3vectors_aws_verified

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_and_get_index_by_name(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = str(uuid4())

    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=1,
        distanceMetric="euclidean",
    )

    get_by_name = client.get_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
    )["index"]

    assert get_by_name["dataType"] == "float32"
    assert get_by_name["dimension"] == 1
    assert get_by_name["distanceMetric"] == "euclidean"
    assert (
        get_by_name["indexArn"]
        == f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"
    )
    assert get_by_name["indexName"] == index_name
    assert get_by_name["vectorBucketName"] == bucket_name


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_and_get_index_by_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=1,
        distanceMetric="euclidean",
    )

    get_by_arn = client.get_index(
        indexArn=f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}",
    )["index"]

    assert get_by_arn["indexName"] == index_name
    assert get_by_arn["vectorBucketName"] == bucket_name


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_index_with_unknown_data_type(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.create_index(
            vectorBucketName=bucket_name,
            indexName=index_name,
            dataType="int",
            dimension=1,
            distanceMetric="euclidean",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected. Value at '/dataType' failed to satisfy constraint: Member must satisfy enum value set: [float32]"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_index_with_unknown_dimension(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.create_index(
            vectorBucketName=bucket_name,
            indexName=index_name,
            dataType="float32",
            dimension=99999,
            distanceMetric="euclidean",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected. Value at '/dimension' failed to satisfy constraint: Member must be between 1 and 4096, inclusive"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_index_with_unknown_distance_metric(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.create_index(
            vectorBucketName=bucket_name,
            indexName=index_name,
            dataType="float32",
            dimension=1,
            distanceMetric="what",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "1 validation error detected. Value at '/distanceMetric' failed to satisfy constraint: Member must satisfy enum value set: [euclidean, cosine]"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_and_get_index_by_name_and_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.get_index(
            vectorBucketName=bucket_name,
            indexArn=f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Must specify either indexArn or both vectorBucketName and indexName"
    )


@aws_verified
@pytest.mark.aws_verified
def test_get_index_by_unknown_bucket(account_id):
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())
    index_name = str(uuid4())
    with pytest.raises(ClientError) as exc:
        client.get_index(
            vectorBucketName=bucket_name,
            indexName=index_name,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified index could not be found"


@aws_verified
@pytest.mark.aws_verified
def test_get_index_by_unknown_name(account_id):
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())
    index_name = str(uuid4())
    client.create_vector_bucket(vectorBucketName=bucket_name)

    try:
        with pytest.raises(ClientError) as exc:
            client.get_index(
                vectorBucketName=bucket_name,
                indexName=index_name,
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "NotFoundException"
        assert err["Message"] == "The specified index could not be found"

    finally:
        client.delete_vector_bucket(vectorBucketName=bucket_name)


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_get_index_by_unknown_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.get_index(
            indexArn=f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified index could not be found"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_and_list_indexes(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}"
    index_name = str(uuid4())

    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=1,
        distanceMetric="euclidean",
    )

    # List by bucket name
    indexes = client.list_indexes(vectorBucketName=bucket_name)["indexes"]
    assert len(indexes) == 1
    assert indexes[0]["vectorBucketName"] == bucket_name
    assert indexes[0]["indexName"] == index_name
    assert (
        indexes[0]["indexArn"]
        == f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"
    )

    # List by bucket ARN
    indexes = client.list_indexes(vectorBucketArn=bucket_arn)["indexes"]
    assert len(indexes) == 1
    assert indexes[0]["vectorBucketName"] == bucket_name

    # Delete Index
    client.delete_index(vectorBucketName=bucket_name, indexName=index_name)

    # Verify it's been deleted
    indexes = client.list_indexes(vectorBucketName=bucket_name)["indexes"]
    assert len(indexes) == 0


@aws_verified
@pytest.mark.aws_verified
def test_list_indexes_by_unknown_bucket_name(account_id):
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.list_indexes(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified vector bucket could not be found"


@aws_verified
@pytest.mark.aws_verified
def test_list_indexes_by_name_and_arn(account_id):
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())
    bucket_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}"

    with pytest.raises(ClientError) as exc:
        client.list_indexes(vectorBucketName=bucket_name, vectorBucketArn=bucket_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Must specify either vectorBucketName or vectorBucketArn but not both"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_delete_bucket_fails_if_index_exists(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=1,
        distanceMetric="euclidean",
    )

    with pytest.raises(ClientError) as exc:
        client.delete_vector_bucket(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert err["Message"] == "The specified vector bucket is not empty"

    # First delete the index
    client.delete_index(vectorBucketName=bucket_name, indexName=index_name)

    # Now we can delete the bucket
    client.delete_vector_bucket(vectorBucketName=bucket_name)
