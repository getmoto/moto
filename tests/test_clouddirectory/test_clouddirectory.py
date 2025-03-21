"""Unit tests for clouddirectory-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_directory():
    client = boto3.client("clouddirectory", region_name="ap-southeast-1")
    resp = client.create_directory()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_directories():
    client = boto3.client("clouddirectory", region_name="ap-southeast-1")
    resp = client.list_directories()

    raise Exception("NotYetImplemented")


@mock_aws
def test_tag_resource():
    client = boto3.client("clouddirectory", region_name="us-east-2")
    resp = client.tag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_untag_resource():
    client = boto3.client("clouddirectory", region_name="us-east-2")
    resp = client.untag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_directory():
    client = boto3.client("clouddirectory", region_name="eu-west-1")
    resp = client.delete_directory()

    raise Exception("NotYetImplemented")


@mock_aws
def test_get_directory():
    client = boto3.client("clouddirectory", region_name="ap-southeast-1")
    resp = client.get_directory()

    raise Exception("NotYetImplemented")
