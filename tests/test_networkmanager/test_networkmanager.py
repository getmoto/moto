"""Unit tests for networkmanager-supported APIs."""

import boto3

from moto import mock_aws
from tests import DEFAULT_ACCOUNT_ID

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
    assert (
        global_network["GlobalNetworkArn"]
        == f"arn:aws:networkmanager:{DEFAULT_ACCOUNT_ID}:global-network/{global_network['GlobalNetworkId']}"
    )
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
    assert (
        core_network["CoreNetworkArn"]
        == f"arn:aws:networkmanager:{DEFAULT_ACCOUNT_ID}:core-network/{core_network['CoreNetworkId']}"
    )
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
def test_tag_resource():
    client = boto3.client("networkmanager")
    gn_id = create_global_network(client)
    cn = client.create_core_network(GlobalNetworkId=gn_id)["CoreNetwork"]

    # Check tagging core-network
    resp = client.tag_resource(
        ResourceArn=cn["CoreNetworkArn"],
        Tags=[{"Key": "Test", "Value": "TestValue-Core"}],
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    updated_cn = client.get_core_network(CoreNetworkId=cn["CoreNetworkId"])[
        "CoreNetwork"
    ]
    assert updated_cn["Tags"] == [{"Key": "Test", "Value": "TestValue-Core"}]

    # Check tagging global-network
    gn_arn = client.describe_global_networks()["GlobalNetworks"][0]["GlobalNetworkArn"]
    resp = client.tag_resource(
        ResourceArn=gn_arn, Tags=[{"Key": "Test", "Value": "TestValue-Global"}]
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    updated_gn = client.describe_global_networks(GlobalNetworkIds=[gn_id])[
        "GlobalNetworks"
    ][0]
    assert len(updated_gn["Tags"]) == 2
    assert updated_gn["Tags"] == [
        {"Key": "Name", "Value": "TestNetwork"},
        {"Key": "Test", "Value": "TestValue-Global"},
    ]


@mock_aws
def test_untag_resource():
    client = boto3.client("networkmanager")
    gn_id = create_global_network(client)
    cn = client.create_core_network(
        GlobalNetworkId=gn_id,
        Tags=[
            {"Key": "Name", "Value": "TestNetwork"},
            {"Key": "DeleteMe", "Value": "DeleteThisTag!"},
        ],
    )["CoreNetwork"]

    # Check untagging core-network
    resp = client.untag_resource(ResourceArn=cn["CoreNetworkArn"], TagKeys=["DeleteMe"])
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    updated_cn = client.get_core_network(CoreNetworkId=cn["CoreNetworkId"])[
        "CoreNetwork"
    ]
    assert len(updated_cn["Tags"]) == 1
    assert updated_cn["Tags"] == [{"Key": "Name", "Value": "TestNetwork"}]


@mock_aws
def test_list_core_networks():
    NUM_CORE_NETWORKS = 3
    client = boto3.client("networkmanager")
    for _ in range(NUM_CORE_NETWORKS):
        gn_id = create_global_network(client)
        client.create_core_network(GlobalNetworkId=gn_id)

    resp = client.list_core_networks()
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


@mock_aws
def test_describe_global_networks():
    NUM_NETWORKS = 3
    client = boto3.client("networkmanager")
    global_ids = []
    for i in range(NUM_NETWORKS):
        global_id = client.create_global_network(
            Description=f"Test global network #{i}",
            Tags=[
                {"Key": "Name", "Value": f"TestNetwork-{i}"},
            ],
        )["GlobalNetwork"]["GlobalNetworkId"]
        global_ids.append(global_id)
    resp = client.describe_global_networks()
    assert len(resp["GlobalNetworks"]) == NUM_NETWORKS

    # Check each global network by ID
    for g_id in global_ids:
        gn = client.describe_global_networks(GlobalNetworkIds=[g_id])["GlobalNetworks"][
            0
        ]
        assert gn["GlobalNetworkId"] == g_id
