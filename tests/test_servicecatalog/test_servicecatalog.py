"""Unit tests for servicecatalog-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_list_portfolio_access():
    client = boto3.client("servicecatalog", region_name="eu-west-1")
    resp = client.list_portfolio_access()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_portfolio():
    client = boto3.client("servicecatalog", region_name="eu-west-1")
    resp = client.delete_portfolio()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_portfolio_share():
    client = boto3.client("servicecatalog", region_name="ap-southeast-1")
    resp = client.delete_portfolio_share()

    raise Exception("NotYetImplemented")
