"""Unit tests for emr-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_get_block_public_access_configuration():
    client = boto3.client("emr", region_name="us-east-2")
    resp = client.get_block_public_access_configuration()

    raise Exception("NotYetImplemented")


@mock_aws
def test_get_block_public_access_configuration():
    client = boto3.client("emr", region_name="ap-southeast-1")
    resp = client.get_block_public_access_configuration()

    raise Exception("NotYetImplemented")


@mock_aws
def test_put_block_public_access_configuration():
    client = boto3.client("emr", region_name="eu-west-1")
    resp = client.put_block_public_access_configuration()

    raise Exception("NotYetImplemented")
