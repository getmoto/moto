import os

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from freezegun import freeze_time
from unittest import SkipTest

from moto import mock_managedblockchain
from . import helpers


@mock_managedblockchain
def test_vote_on_proposal_one_member_total_yes():
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
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
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

    # List proposal votes
    response = conn.list_proposal_votes(NetworkId=network_id, ProposalId=proposal_id)
    response["ProposalVotes"][0]["MemberId"].should.equal(member_id)

    # Get proposal details - should be APPROVED
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["Status"].should.equal("APPROVED")
    response["Proposal"]["YesVoteCount"].should.equal(1)
    response["Proposal"]["NoVoteCount"].should.equal(0)
    response["Proposal"]["OutstandingVoteCount"].should.equal(0)


@mock_managedblockchain
def test_vote_on_proposal_one_member_total_no():
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
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )
    proposal_id = response["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("IN_PROGRESS")

    # Vote no
    response = conn.vote_on_proposal(
        NetworkId=network_id, ProposalId=proposal_id, VoterMemberId=member_id, Vote="NO"
    )

    # List proposal votes
    response = conn.list_proposal_votes(NetworkId=network_id, ProposalId=proposal_id)
    response["ProposalVotes"][0]["MemberId"].should.equal(member_id)

    # Get proposal details - should be REJECTED
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["Status"].should.equal("REJECTED")
    response["Proposal"]["YesVoteCount"].should.equal(0)
    response["Proposal"]["NoVoteCount"].should.equal(1)
    response["Proposal"]["OutstandingVoteCount"].should.equal(0)


@mock_managedblockchain
def test_vote_on_proposal_yes_greater_than():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    votingpolicy = {
        "ApprovalThresholdPolicy": {
            "ThresholdPercentage": 50,
            "ProposalDurationInHours": 24,
            "ThresholdComparator": "GREATER_THAN",
        }
    }

    # Create network
    response = conn.create_network(
        Name="testnetwork1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )
    network_id = response["NetworkId"]
    member_id = response["MemberId"]

    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    # Vote yes
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    invitation_id = response["Invitations"][0]["InvitationId"]

    # Create the member
    response = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False, "Test Member 2"
        ),
    )
    member_id2 = response["MemberId"]

    # Create another proposal
    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    # Vote yes with member 1
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("IN_PROGRESS")

    # Vote no with member 2
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id2,
        Vote="NO",
    )

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["Status"].should.equal("REJECTED")


@mock_managedblockchain
def test_vote_on_proposal_no_greater_than():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    votingpolicy = {
        "ApprovalThresholdPolicy": {
            "ThresholdPercentage": 50,
            "ProposalDurationInHours": 24,
            "ThresholdComparator": "GREATER_THAN",
        }
    }

    # Create network
    response = conn.create_network(
        Name="testnetwork1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )
    network_id = response["NetworkId"]
    member_id = response["MemberId"]

    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    # Vote yes
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    invitation_id = response["Invitations"][0]["InvitationId"]

    # Create the member
    response = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False, "Test Member 2"
        ),
    )
    member_id2 = response["MemberId"]

    # Create another proposal
    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    # Vote no with member 1
    response = conn.vote_on_proposal(
        NetworkId=network_id, ProposalId=proposal_id, VoterMemberId=member_id, Vote="NO"
    )

    # Vote no with member 2
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id2,
        Vote="NO",
    )

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("REJECTED")


@mock_managedblockchain
def test_vote_on_proposal_expiredproposal():
    if os.environ.get("TEST_SERVER_MODE", "false").lower() == "true":
        raise SkipTest("Cant manipulate time in server mode")

    votingpolicy = {
        "ApprovalThresholdPolicy": {
            "ThresholdPercentage": 50,
            "ProposalDurationInHours": 1,
            "ThresholdComparator": "GREATER_THAN_OR_EQUAL_TO",
        }
    }

    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with freeze_time("2015-01-01 12:00:00"):
        # Create network - need a good network
        response = conn.create_network(
            Name="testnetwork1",
            Framework="HYPERLEDGER_FABRIC",
            FrameworkVersion="1.2",
            FrameworkConfiguration=helpers.default_frameworkconfiguration,
            VotingPolicy=votingpolicy,
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

    with freeze_time("2015-02-01 12:00:00"):
        # Vote yes - should set status to expired
        with pytest.raises(ClientError) as ex:
            conn.vote_on_proposal(
                NetworkId=network_id,
                ProposalId=proposal_id,
                VoterMemberId=member_id,
                Vote="YES",
            )
        err = ex.value.response["Error"]
        err["Code"].should.equal("InvalidRequestException")
        err["Message"].should.contain(
            f"Proposal {proposal_id} is expired and you cannot vote on it."
        )

        # Get proposal details - should be EXPIRED
        response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
        response["Proposal"]["Status"].should.equal("EXPIRED")


@mock_managedblockchain
def test_vote_on_proposal_status_check():
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

    # Create 2 more members
    for counter in range(2, 4):
        response = conn.create_proposal(
            NetworkId=network_id,
            MemberId=member_id,
            Actions=helpers.default_policy_actions,
        )
        proposal_id = response["ProposalId"]

        # Vote yes
        response = conn.vote_on_proposal(
            NetworkId=network_id,
            ProposalId=proposal_id,
            VoterMemberId=member_id,
            Vote="YES",
        )

    memberidlist = [None, None, None]
    memberidlist[0] = member_id
    for counter in range(2, 4):
        # Get the invitation
        response = conn.list_invitations()
        invitation_id = helpers.select_invitation_id_for_network(
            response["Invitations"], network_id, "PENDING"
        )[0]

        # Create the member
        response = conn.create_member(
            InvitationId=invitation_id,
            NetworkId=network_id,
            MemberConfiguration=helpers.create_member_configuration(
                "testmember" + str(counter),
                "admin",
                "Admin12345",
                False,
                "Test Member " + str(counter),
            ),
        )
        member_id = response["MemberId"]
        memberidlist[counter - 1] = member_id

    # Should be no more pending invitations
    response = conn.list_invitations()
    pendinginvs = helpers.select_invitation_id_for_network(
        response["Invitations"], network_id, "PENDING"
    )
    pendinginvs.should.have.length_of(0)

    # Create another proposal
    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    # Vote yes with member 1
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=memberidlist[0],
        Vote="YES",
    )

    # Vote yes with member 2
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=memberidlist[1],
        Vote="YES",
    )

    # Get proposal details - now approved (2 yes, 1 outstanding)
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("APPROVED")

    # Should be one pending invitation
    response = conn.list_invitations()
    pendinginvs = helpers.select_invitation_id_for_network(
        response["Invitations"], network_id, "PENDING"
    )
    pendinginvs.should.have.length_of(1)

    # Vote with member 3 - should throw an exception and not create a new invitation
    with pytest.raises(ClientError) as ex:
        conn.vote_on_proposal(
            NetworkId=network_id,
            ProposalId=proposal_id,
            VoterMemberId=memberidlist[2],
            Vote="YES",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.contain("and you cannot vote on it")

    # Should still be one pending invitation
    response = conn.list_invitations()
    pendinginvs = helpers.select_invitation_id_for_network(
        response["Invitations"], network_id, "PENDING"
    )
    pendinginvs.should.have.length_of(1)


@mock_managedblockchain
def test_vote_on_proposal_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.vote_on_proposal(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            ProposalId="p-ABCDEFGHIJKLMNOP0123456789",
            VoterMemberId="m-ABCDEFGHIJKLMNOP0123456789",
            Vote="YES",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_vote_on_proposal_badproposal():
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

    with pytest.raises(ClientError) as ex:
        conn.vote_on_proposal(
            NetworkId=network_id,
            ProposalId="p-ABCDEFGHIJKLMNOP0123456789",
            VoterMemberId="m-ABCDEFGHIJKLMNOP0123456789",
            Vote="YES",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Proposal p-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_vote_on_proposal_badmember():
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
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    with pytest.raises(ClientError) as ex:
        conn.vote_on_proposal(
            NetworkId=network_id,
            ProposalId=proposal_id,
            VoterMemberId="m-ABCDEFGHIJKLMNOP0123456789",
            Vote="YES",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_vote_on_proposal_badvote():
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
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    with pytest.raises(ClientError) as ex:
        conn.vote_on_proposal(
            NetworkId=network_id,
            ProposalId=proposal_id,
            VoterMemberId=member_id,
            Vote="FOO",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain("Invalid request body")


@mock_managedblockchain
def test_vote_on_proposal_alreadyvoted():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    votingpolicy = {
        "ApprovalThresholdPolicy": {
            "ThresholdPercentage": 50,
            "ProposalDurationInHours": 24,
            "ThresholdComparator": "GREATER_THAN",
        }
    }

    # Create network - need a good network
    response = conn.create_network(
        Name="testnetwork1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )
    network_id = response["NetworkId"]
    member_id = response["MemberId"]

    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    # Vote yes
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    invitation_id = response["Invitations"][0]["InvitationId"]

    # Create the member
    response = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False, "Test Member 2"
        ),
    )

    # Create another proposal
    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )

    proposal_id = response["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("IN_PROGRESS")

    # Vote yes with member 1
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Vote yes with member 1 again
    with pytest.raises(ClientError) as ex:
        conn.vote_on_proposal(
            NetworkId=network_id,
            ProposalId=proposal_id,
            VoterMemberId=member_id,
            Vote="YES",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceAlreadyExistsException")
    err["Message"].should.contain(
        f"Member {member_id} has already voted on proposal {proposal_id}."
    )


@mock_managedblockchain
def test_list_proposal_votes_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_proposal_votes(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            ProposalId="p-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_list_proposal_votes_badproposal():
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

    with pytest.raises(ClientError) as ex:
        conn.list_proposal_votes(
            NetworkId=network_id, ProposalId="p-ABCDEFGHIJKLMNOP0123456789"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Proposal p-ABCDEFGHIJKLMNOP0123456789 not found")
