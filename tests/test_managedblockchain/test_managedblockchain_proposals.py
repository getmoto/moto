import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_managedblockchain
from . import helpers


@mock_managedblockchain
def test_create_proposal():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Create network
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

    # Create proposal
    proposal_id = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )["ProposalId"]
    assert proposal_id.startswith("p-")
    assert len(proposal_id) == 28

    # Find in full list
    proposals = conn.list_proposals(NetworkId=network_id)["Proposals"]
    assert len(proposals) == 1
    assert proposals[0]["ProposalId"] == proposal_id

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    assert response["Proposal"]["NetworkId"] == network_id


@mock_managedblockchain
def test_create_proposal_withopts():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Create network
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

    # Create proposal
    proposal_id = conn.create_proposal(
        NetworkId=network_id,
        MemberId=member_id,
        Actions=helpers.default_policy_actions,
        Description="Adding a new member",
    )["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    assert response["Proposal"]["Description"] == "Adding a new member"


@mock_managedblockchain
def test_create_proposal_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.create_proposal(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            Actions=helpers.default_policy_actions,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_create_proposal_badmember():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Create network - need a good network
    network_id = conn.create_network(
        Name="testnetwork1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )["NetworkId"]

    with pytest.raises(ClientError) as ex:
        conn.create_proposal(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            Actions=helpers.default_policy_actions,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_create_proposal_badinvitationacctid():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Must be 12 digits
    actions = {"Invitations": [{"Principal": "1234567890"}]}

    # Create network - need a good network
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

    with pytest.raises(ClientError) as ex:
        conn.create_proposal(NetworkId=network_id, MemberId=member_id, Actions=actions)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert "Account ID format specified in proposal is not valid" in err["Message"]


@mock_managedblockchain
def test_create_proposal_badremovalmemid():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Must be 12 digits
    actions = {"Removals": [{"MemberId": "m-ABCDEFGHIJKLMNOP0123456789"}]}

    # Create network - need a good network
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

    with pytest.raises(ClientError) as ex:
        conn.create_proposal(NetworkId=network_id, MemberId=member_id, Actions=actions)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert "Member ID format specified in proposal is not valid" in err["Message"]


@mock_managedblockchain
def test_list_proposal_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_proposals(NetworkId="n-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_get_proposal_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_proposal(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            ProposalId="p-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_get_proposal_badproposal():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Create network - need a good network
    network_id = conn.create_network(
        Name="testnetwork1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )["NetworkId"]

    with pytest.raises(ClientError) as ex:
        conn.get_proposal(
            NetworkId=network_id, ProposalId="p-ABCDEFGHIJKLMNOP0123456789"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Proposal p-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]
