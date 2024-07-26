"""Unit tests for transfer-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_user():
    client = boto3.client("transfer", region_name="ap-southeast-1")
    resp = client.create_user()

    raise Exception("NotYetImplemented")


@mock_aws
def test_describe_user():
    client = boto3.client("transfer", region_name="ap-southeast-1")
    resp = client.describe_user()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_user():
    client = boto3.client("transfer", region_name="eu-west-1")
    resp = client.delete_user()

    raise Exception("NotYetImplemented")


@mock_aws
def test_import_ssh_public_key():
    client = boto3.client("transfer", region_name="us-east-2")
    resp = client.import_ssh_public_key()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_ssh_public_key():
    client = boto3.client("transfer", region_name="ap-southeast-1")
    resp = client.delete_ssh_public_key()

    raise Exception("NotYetImplemented")
