import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

from . import helpers


@mock_aws
def test_create_network():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    response = conn.create_network(
        Name="testnetwork1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )
    network_id = response["NetworkId"]
    member_id = response["MemberId"]
    assert network_id.startswith("n-")
    assert len(network_id) == 28
    assert member_id.startswith("m-")
    assert len(member_id) == 28

    # Find in full list
    mbcnetworks = conn.list_networks()["Networks"]
    assert len(mbcnetworks) == 1
    assert mbcnetworks[0]["Name"] == "testnetwork1"

    # Get network details
    response = conn.get_network(NetworkId=network_id)
    assert response["Network"]["Name"] == "testnetwork1"


@mock_aws
def test_create_network_with_description():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    response = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )
    network_id = response["NetworkId"]

    # Find in full list
    mbcnetworks = conn.list_networks()["Networks"]
    assert len(mbcnetworks) == 1
    assert mbcnetworks[0]["Description"] == "Test Network 1"

    # Get network details
    response = conn.get_network(NetworkId=network_id)
    assert response["Network"]["Description"] == "Test Network 1"


@mock_aws
def test_create_network_noframework():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.create_network(
            Name="testnetwork1",
            Description="Test Network 1",
            Framework="HYPERLEDGER_VINYL",
            FrameworkVersion="1.2",
            FrameworkConfiguration=helpers.default_frameworkconfiguration,
            VotingPolicy=helpers.default_votingpolicy,
            MemberConfiguration=helpers.default_memberconfiguration,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert "Invalid request body" in err["Message"]


@mock_aws
def test_create_network_badframeworkver():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.create_network(
            Name="testnetwork1",
            Description="Test Network 1",
            Framework="HYPERLEDGER_FABRIC",
            FrameworkVersion="1.X",
            FrameworkConfiguration=helpers.default_frameworkconfiguration,
            VotingPolicy=helpers.default_votingpolicy,
            MemberConfiguration=helpers.default_memberconfiguration,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert (
        "Invalid version 1.X requested for framework HYPERLEDGER_FABRIC"
        in err["Message"]
    )


@mock_aws
def test_create_network_badedition():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    frameworkconfiguration = {"Fabric": {"Edition": "SUPER"}}

    with pytest.raises(ClientError) as ex:
        conn.create_network(
            Name="testnetwork1",
            Description="Test Network 1",
            Framework="HYPERLEDGER_FABRIC",
            FrameworkVersion="1.2",
            FrameworkConfiguration=frameworkconfiguration,
            VotingPolicy=helpers.default_votingpolicy,
            MemberConfiguration=helpers.default_memberconfiguration,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert "Invalid request body" in err["Message"]


@mock_aws
def test_get_network_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_network(NetworkId="n-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]
