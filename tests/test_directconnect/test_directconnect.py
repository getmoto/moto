"""Unit tests for directconnect-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_describe_connections():
    client = boto3.client("directconnect", region_name="ap-southeast-1")
    resp = client.describe_connections()

    raise Exception("NotYetImplemented")
