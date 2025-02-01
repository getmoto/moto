"""Unit tests for cloudhsmv2-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_list_tags():
    client = boto3.client("cloudhsmv2", region_name="eu-west-1")
    resp = client.list_tags()

    raise Exception("NotYetImplemented")
