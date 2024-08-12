"""Unit tests for qldb-supported APIs."""

import boto3
import pytest

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@pytest.fixture(name="client")
def fixture_transfer_client():
    with mock_aws():
        yield boto3.client("qldb", region_name="us-east-1")


@mock_aws
def test_create_describe_update_and_delete_ledger(client):
    connection = client.create_ledger()
    connection = client.describe_ledger()
    connection = client.update_ledger()
    connection = client.delete_ledger()


@mock_aws
def test_tag_resource_and_list_tags_for_resource(client):
    resp = client.tag_resource()
    resp = client.list_tags_for_resource()
