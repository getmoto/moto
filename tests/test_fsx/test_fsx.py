"""Unit tests for fsx-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_file_system():
    client = boto3.client("fsx", region_name="eu-west-1")
    resp = client.create_file_system()

    raise Exception("NotYetImplemented")
