"""Unit tests for qldb-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_describe_ledger():
    client = boto3.client("qldb", region_name="eu-west-1")
    resp = client.describe_ledger()

    raise Exception("NotYetImplemented")


@mock_aws
def test_create_ledger():
    client = boto3.client("qldb", region_name="us-east-2")
    resp = client.create_ledger()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_ledger():
    client = boto3.client("qldb", region_name="eu-west-1")
    resp = client.delete_ledger()

    raise Exception("NotYetImplemented")


@mock_aws
def test_update_ledger():
    client = boto3.client("qldb", region_name="us-east-2")
    resp = client.update_ledger()

    raise Exception("NotYetImplemented")


@mock_aws
def test_tag_resource():
    client = boto3.client("qldb", region_name="ap-southeast-1")
    resp = client.tag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("qldb", region_name="eu-west-1")
    resp = client.list_tags_for_resource()

    raise Exception("NotYetImplemented")
