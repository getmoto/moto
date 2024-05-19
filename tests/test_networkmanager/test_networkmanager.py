"""Unit tests for networkmanager-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_global_network():
    client = boto3.client("networkmanager")
    resp = client.create_global_network(
        Description="Test global network",
        Tags=[
            {"Key": "Name", "Value": "TestNetwork"},
        ],
    )

    global_network = resp["GlobalNetwork"]
    assert global_network["Description"] == "Test global network"
    assert global_network["Tags"] == [{"Key": "Name", "Value": "TestNetwork"}]
    assert global_network["State"] == "PENDING"


@mock_aws
def test_create_core_network():
    client = boto3.client("networkmanager")
    # Create a global network
    global_network_id = client.create_global_network(
        Description="Test global network",
        Tags=[
            {"Key": "Name", "Value": "TestNetwork"},
        ],
    )["GlobalNetwork"]["GlobalNetworkId"]

    resp = client.create_core_network(
        GlobalNetworkId=global_network_id,
        Description="Test core network",
        Tags=[
            {"Key": "Name", "Value": "TestNetwork"},
        ],
        PolicyDocument="policy-document",
        ClientToken="client-token",
    )

    core_network = resp["CoreNetwork"]
    assert core_network["GlobalNetworkId"] == global_network_id
    assert core_network["Description"] == "Test core network"
    assert len(core_network["Tags"]) == 1
