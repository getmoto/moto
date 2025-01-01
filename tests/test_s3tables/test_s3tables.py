"""Unit tests for s3tables-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_table_bucket():
    client = boto3.client("s3tables", region_name="us-east-1")
    resp = client.create_table_bucket(name="mytablebucket")
    assert "arn" in resp





@mock_aws
def test_list_table_buckets():
    client = boto3.client("s3tables", region_name="us-east-2")
    resp = client.list_table_buckets()

    raise Exception("NotYetImplemented")


@mock_aws
def test_get_table_bucket():
    client = boto3.client("s3tables", region_name="eu-west-1")
    resp = client.get_table_bucket()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_table_bucket():
    client = boto3.client("s3tables", region_name="eu-west-1")
    resp = client.delete_table_bucket()

    raise Exception("NotYetImplemented")
