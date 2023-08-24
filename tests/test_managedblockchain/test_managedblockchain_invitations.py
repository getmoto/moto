import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_managedblockchain
from . import helpers


@mock_managedblockchain
def test_create_2_invitations():
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
        Actions=helpers.multiple_policy_actions,
    )["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    assert response["Proposal"]["NetworkId"] == network_id
    assert response["Proposal"]["Status"] == "IN_PROGRESS"

    # Vote yes
    conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    assert len(response["Invitations"]) == 2
    assert response["Invitations"][0]["NetworkSummary"]["Id"] == network_id
    assert response["Invitations"][0]["Status"] == "PENDING"
    assert response["Invitations"][1]["NetworkSummary"]["Id"] == network_id
    assert response["Invitations"][1]["Status"] == "PENDING"


@mock_managedblockchain
def test_reject_invitation():
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

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    assert response["Proposal"]["NetworkId"] == network_id
    assert response["Proposal"]["Status"] == "IN_PROGRESS"

    # Vote yes
    conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    assert response["Invitations"][0]["NetworkSummary"]["Id"] == network_id
    assert response["Invitations"][0]["Status"] == "PENDING"
    invitation_id = response["Invitations"][0]["InvitationId"]

    # Reject - thanks but no thanks
    conn.reject_invitation(InvitationId=invitation_id)

    # Check the invitation status
    response = conn.list_invitations()
    assert response["Invitations"][0]["InvitationId"] == invitation_id
    assert response["Invitations"][0]["Status"] == "REJECTED"


@mock_managedblockchain
def test_reject_invitation_badinvitation():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

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

    proposal_id = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )["ProposalId"]

    conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    with pytest.raises(ClientError) as ex:
        conn.reject_invitation(InvitationId="in-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "InvitationId in-ABCDEFGHIJKLMNOP0123456789 not found." in err["Message"]
