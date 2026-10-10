"""Unit tests for s3vectors resource tagging APIs."""

from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from tests.test_s3vectors import s3vectors_aws_verified


@s3vectors_aws_verified(create_bucket=False)
@pytest.mark.aws_verified
def test_create_vector_bucket_with_tags():
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())

    try:
        client.create_vector_bucket(
            vectorBucketName=bucket_name,
            tags={"env": "dev", "project": "search"},
        )
        bucket = client.get_vector_bucket(vectorBucketName=bucket_name)["vectorBucket"]
        bucket_arn = bucket["vectorBucketArn"]

        res = client.list_tags_for_resource(resourceArn=bucket_arn)
        assert res["tags"] == {"env": "dev", "project": "search"}
    finally:
        client.delete_vector_bucket(vectorBucketName=bucket_name)


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_tag_and_untag_vector_bucket(bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket = client.get_vector_bucket(vectorBucketName=bucket_name)["vectorBucket"]
    bucket_arn = bucket["vectorBucketArn"]

    res = client.list_tags_for_resource(resourceArn=bucket_arn)
    assert res["tags"] == {}

    client.tag_resource(
        resourceArn=bucket_arn,
        tags={"key1": "val1", "key2": "val2", "key3": "val3"},
    )
    res = client.list_tags_for_resource(resourceArn=bucket_arn)
    assert res["tags"] == {"key1": "val1", "key2": "val2", "key3": "val3"}

    client.untag_resource(resourceArn=bucket_arn, tagKeys=["key1", "key3"])
    res = client.list_tags_for_resource(resourceArn=bucket_arn)
    assert res["tags"] == {"key2": "val2"}


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_create_index_with_tags(bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=128,
        distanceMetric="euclidean",
        tags={"env": "test", "component": "indexer"},
    )

    index = client.get_index(vectorBucketName=bucket_name, indexName=index_name)[
        "index"
    ]
    index_arn = index["indexArn"]

    res = client.list_tags_for_resource(resourceArn=index_arn)
    assert res["tags"] == {"env": "test", "component": "indexer"}


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_tag_and_untag_index(bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    index_name = str(uuid4())

    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=64,
        distanceMetric="cosine",
    )

    index = client.get_index(vectorBucketName=bucket_name, indexName=index_name)[
        "index"
    ]
    index_arn = index["indexArn"]

    res = client.list_tags_for_resource(resourceArn=index_arn)
    assert res["tags"] == {}

    client.tag_resource(
        resourceArn=index_arn,
        tags={"stage": "staging", "tier": "gold"},
    )
    res = client.list_tags_for_resource(resourceArn=index_arn)
    assert res["tags"] == {"stage": "staging", "tier": "gold"}

    client.untag_resource(resourceArn=index_arn, tagKeys=["tier"])
    res = client.list_tags_for_resource(resourceArn=index_arn)
    assert res["tags"] == {"stage": "staging"}


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_tag_resource_not_found(bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")
    fake_arn = f"arn:aws:s3vectors:us-east-1:123456789012:bucket/{uuid4()!s}"

    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(resourceArn=fake_arn)
    assert exc.value.response["Error"]["Code"] == "NotFoundException"

    with pytest.raises(ClientError) as exc:
        client.tag_resource(resourceArn=fake_arn, tags={"k": "v"})
    assert exc.value.response["Error"]["Code"] == "NotFoundException"

    with pytest.raises(ClientError) as exc:
        client.untag_resource(resourceArn=fake_arn, tagKeys=["k"])
    assert exc.value.response["Error"]["Code"] == "NotFoundException"


@s3vectors_aws_verified(create_bucket=False)
@pytest.mark.aws_verified
def test_tags_cleaned_up_on_resource_deletion():
    client = boto3.client("s3vectors", region_name="us-east-1")
    bucket_name = str(uuid4())
    index_name = str(uuid4())

    client.create_vector_bucket(
        vectorBucketName=bucket_name,
        tags={"type": "bucket"},
    )
    bucket = client.get_vector_bucket(vectorBucketName=bucket_name)["vectorBucket"]
    bucket_arn = bucket["vectorBucketArn"]

    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=32,
        distanceMetric="euclidean",
        tags={"type": "index"},
    )
    index = client.get_index(vectorBucketName=bucket_name, indexName=index_name)[
        "index"
    ]
    index_arn = index["indexArn"]

    assert client.list_tags_for_resource(resourceArn=bucket_arn)["tags"] == {
        "type": "bucket"
    }
    assert client.list_tags_for_resource(resourceArn=index_arn)["tags"] == {
        "type": "index"
    }

    client.delete_index(vectorBucketName=bucket_name, indexName=index_name)
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(resourceArn=index_arn)
    assert exc.value.response["Error"]["Code"] == "NotFoundException"

    client.delete_vector_bucket(vectorBucketName=bucket_name)
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(resourceArn=bucket_arn)
    assert exc.value.response["Error"]["Code"] == "NotFoundException"
