"""Unit tests for networkfirewall-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_firewall():
    client = boto3.client("network-firewall", region_name="us-east-1")
    firewall = client.create_firewall(
        FirewallName="test-firewall",
        FirewallPolicyArn="arn:aws:network-firewall:ap-southeast-1:123456789012:firewall-policy/test-policy",
    )["Firewall"]

    assert firewall["FirewallName"] == "test-firewall"


@mock_aws
def test_describe_logging_configuration():
    client = boto3.client("network-firewall", region_name="eu-west-1")
    resp = client.describe_logging_configuration()

    raise Exception("NotYetImplemented")


@mock_aws
def test_update_logging_configuration():
    client = boto3.client("network-firewall", region_name="ap-southeast-1")
    resp = client.update_logging_configuration()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_firewalls():
    client = boto3.client("network-firewall", region_name="ap-southeast-1")
    resp = client.list_firewalls()

    raise Exception("NotYetImplemented")


@mock_aws
def test_describe_firewall():
    client = boto3.client("network-firewall", region_name="ap-southeast-1")
    resp = client.describe_firewall()

    raise Exception("NotYetImplemented")
