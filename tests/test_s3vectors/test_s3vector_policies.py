"""Unit tests for s3vectors-supported APIs."""

import json
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
def test_put_vector_bucket_policy_by_name(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    client.put_vector_bucket_policy(
        vectorBucketName=bucket_name,
        policy=json.dumps(_get_policy(account_id)),
    )

    policy = client.get_vector_bucket_policy(vectorBucketName=bucket_name)["policy"]
    assert json.loads(policy) == _get_policy(account_id)


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vector_bucket_policy_by_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    get_by_name = client.get_vector_bucket(vectorBucketName=bucket_name)["vectorBucket"]
    bucket_arn = get_by_name["vectorBucketArn"]

    client.put_vector_bucket_policy(
        vectorBucketArn=bucket_arn,
        policy=json.dumps(_get_policy(account_id)),
    )

    policy = client.get_vector_bucket_policy(vectorBucketArn=bucket_arn)["policy"]
    assert json.loads(policy) == _get_policy(account_id)


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_get_default_vector_bucket_policy(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_vector_bucket_policy(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified vector bucket policy could not be found"


@aws_verified
@pytest.mark.aws_verified
def test_get_vector_bucket_policy_for_unknown_bucket(account_id):
    client = boto3.client("s3vectors", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_vector_bucket_policy(vectorBucketName=str(uuid4()))
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified vector bucket could not be found"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_delete_vector_bucket_policy_by_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    get_by_name = client.get_vector_bucket(vectorBucketName=bucket_name)["vectorBucket"]
    bucket_arn = get_by_name["vectorBucketArn"]

    client.put_vector_bucket_policy(
        vectorBucketArn=bucket_arn,
        policy=json.dumps(_get_policy(account_id)),
    )

    client.delete_vector_bucket_policy(vectorBucketArn=bucket_arn)

    with pytest.raises(ClientError) as exc:
        client.get_vector_bucket_policy(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified vector bucket policy could not be found"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_delete_vector_bucket_policy_by_name(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    client.put_vector_bucket_policy(
        vectorBucketName=bucket_name,
        policy=json.dumps(_get_policy(account_id)),
    )

    client.delete_vector_bucket_policy(vectorBucketName=bucket_name)

    with pytest.raises(ClientError) as exc:
        client.get_vector_bucket_policy(vectorBucketName=bucket_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified vector bucket policy could not be found"


def _get_policy(account_id):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{account_id}:root"},
                "Action": "s3vectors:*",
                "Resource": f"arn:aws:s3vectors:aws-region:{account_id}:bucket/amzn-s3-demo-vector-bucket",
            }
        ],
    }
