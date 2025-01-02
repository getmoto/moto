"""Unit tests for s3tables-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_table_bucket():
    client = boto3.client("s3tables", region_name="us-east-1")
    response = client.create_table_bucket(name="foo")
    assert "arn" in response
    assert response["arn"].endswith("foo")


@mock_aws
def test_list_table_buckets():
    client = boto3.client("s3tables", region_name="us-east-2")
    client.create_table_bucket(name="foo")
    response = client.list_table_buckets(prefix="foo")
    assert "tableBuckets" in response
    assert len(response["tableBuckets"]) == 1
    assert response["tableBuckets"][0]["name"] == "foo"


@mock_aws
def test_list_table_buckets_pagination():
    client = boto3.client("s3tables", region_name="us-east-2")
    client.create_table_bucket(name="foo")
    client.create_table_bucket(name="bar")
    response = client.list_table_buckets(maxBuckets=1)

    assert len(response["tableBuckets"]) == 1
    assert "continuationToken" in response

    response = client.list_table_buckets(maxBuckets=1, continuationToken=response["continuationToken"])

    assert len(response["tableBuckets"]) == 1
    assert "continuationToken" not in response
    assert response["tableBuckets"][0]["name"] == "bar"


@mock_aws
def test_get_table_bucket():
    client = boto3.client("s3tables", region_name="us-east-1")
    response = client.create_table_bucket(name="foo")

    assert client.get_table_bucket(tableBucketARN=response["arn"])["name"] == "foo"


@mock_aws
def test_delete_table_bucket():
    client = boto3.client("s3tables", region_name="eu-west-1")
    resp = client.delete_table_bucket()

    raise Exception("NotYetImplemented")
