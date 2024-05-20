"""Unit tests for networkmanager-supported APIs."""

import boto3
import pytest

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


def create_global_network(client) -> str:
    return client.create_global_network(
        Description="Test global network",
        Tags=[
            {"Key": "Name", "Value": "TestNetwork"},
        ],
    )["GlobalNetwork"]["GlobalNetworkId"]


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


@mock_aws
def test_delete_core_network():
    client = boto3.client("networkmanager")
    gn_id = create_global_network(client)
    core_network = client.create_core_network(GlobalNetworkId=gn_id)
    cn_id = core_network["CoreNetwork"]["CoreNetworkId"]
    assert len(client.list_core_networks()["CoreNetworks"]) == 1
    resp = client.delete_core_network(CoreNetworkId=cn_id)
    assert resp["CoreNetwork"]["CoreNetworkId"] == cn_id
    assert resp["CoreNetwork"]["State"] == "DELETING"
    assert len(client.list_core_networks()["CoreNetworks"]) == 0


@mock_aws
@pytest.mark.skip(reason="NotYetImplemented")
def test_tag_resource():
    client = boto3.client("networkmanager")
    resp = client.tag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
@pytest.mark.skip(reason="NotYetImplemented")
def test_untag_resource():
    client = boto3.client("networkmanager")
    resp = client.untag_resource()

    raise Exception("NotYetImplemented")


@mock_aws
def test_list_core_networks():
    NUM_CORE_NETWORKS = 3
    client = boto3.client("networkmanager")
    for _ in range(NUM_CORE_NETWORKS):
        gn_id = create_global_network(client)
        client.create_core_network(GlobalNetworkId=gn_id)

    resp = client.list_core_networks()
    pytest.set_trace()
    assert len(resp["CoreNetworks"]) == NUM_CORE_NETWORKS


@mock_aws
def test_get_core_network():
    client = boto3.client("networkmanager")
    gn_id = create_global_network(client)
    cn_id = client.create_core_network(
        GlobalNetworkId=gn_id,
        Description="Test core network",
        Tags=[
            {"Key": "Name", "Value": "TestNetwork"},
        ],
        PolicyDocument="policy-document",
        ClientToken="client-token",
    )["CoreNetwork"]["CoreNetworkId"]

    resp = client.get_core_network(CoreNetworkId=cn_id)
    assert resp["CoreNetwork"]["CoreNetworkId"] == cn_id
    assert resp["CoreNetwork"]["Description"] == "Test core network"
    assert len(resp["CoreNetwork"]["Tags"]) == 1
