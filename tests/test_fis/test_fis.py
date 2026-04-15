"""Unit tests for fis-supported APIs."""
import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_aws
def test_create_experiment_template():
    client = boto3.client("fis", region_name="ap-southeast-1")
    resp = client.create_experiment_template()

    raise Exception("NotYetImplemented")


@mock_aws
def test_delete_experiment_template():
    client = boto3.client("fis", region_name="eu-west-1")
    resp = client.delete_experiment_template()

    raise Exception("NotYetImplemented")


@mock_aws
def test_tag_resource():
    client = boto3.client("fis", region_name="eu-west-1")
    resp = client.tag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_untag_resource():
    client = boto3.client("fis", region_name="us-east-2")
    resp = client.untag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("fis", region_name="us-east-2")
    resp = client.list_tags_for_resource()

    raise Exception("NotYetImplemented")
