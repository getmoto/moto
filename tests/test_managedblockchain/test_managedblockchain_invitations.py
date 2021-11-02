import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

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
    response = conn.create_proposal(
        NetworkId=network_id,
        MemberId=member_id,
        Actions=helpers.multiple_policy_actions,
    )
    proposal_id = response["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("IN_PROGRESS")

    # Vote yes
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    response["Invitations"].should.have.length_of(2)
    response["Invitations"][0]["NetworkSummary"]["Id"].should.equal(network_id)
    response["Invitations"][0]["Status"].should.equal("PENDING")
    response["Invitations"][1]["NetworkSummary"]["Id"].should.equal(network_id)
    response["Invitations"][1]["Status"].should.equal("PENDING")


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
    response = conn.create_proposal(
        NetworkId=network_id,
        MemberId=member_id,
        Actions=helpers.default_policy_actions,
    )
    proposal_id = response["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("IN_PROGRESS")

    # Vote yes
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    response["Invitations"][0]["NetworkSummary"]["Id"].should.equal(network_id)
    response["Invitations"][0]["Status"].should.equal("PENDING")
    invitation_id = response["Invitations"][0]["InvitationId"]

    # Reject - thanks but no thanks
    response = conn.reject_invitation(InvitationId=invitation_id)

    # Check the invitation status
    response = conn.list_invitations()
    response["Invitations"][0]["InvitationId"].should.equal(invitation_id)
    response["Invitations"][0]["Status"].should.equal("REJECTED")


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

    response = conn.create_proposal(
        NetworkId=network_id,
        MemberId=member_id,
        Actions=helpers.default_policy_actions,
    )

    proposal_id = response["ProposalId"]

    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    with pytest.raises(ClientError) as ex:
        conn.reject_invitation(InvitationId="in-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain(
        "InvitationId in-ABCDEFGHIJKLMNOP0123456789 not found."
    )
