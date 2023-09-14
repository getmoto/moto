import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_managedblockchain
from . import helpers


class TestManagedBlockchainInvitations:
    mock = mock_managedblockchain()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        cls.conn = boto3.client("managedblockchain", region_name="us-east-1")
        response = cls.conn.create_network(
            Name="testnetwork1",
            Framework="HYPERLEDGER_FABRIC",
            FrameworkVersion="1.2",
            FrameworkConfiguration=helpers.default_frameworkconfiguration,
            VotingPolicy=helpers.default_votingpolicy,
            MemberConfiguration=helpers.default_memberconfiguration,
        )
        cls.network_id = response["NetworkId"]
        cls.member_id = response["MemberId"]

    @classmethod
    def teardown_class(cls):
        cls.mock.stop()

    def test_create_2_invitations(self):
        # Create proposal
        proposal_id = self.conn.create_proposal(
            NetworkId=self.network_id,
            MemberId=self.member_id,
            Actions=helpers.multiple_policy_actions,
        )["ProposalId"]

        # Get proposal details
        response = self.conn.get_proposal(
            NetworkId=self.network_id, ProposalId=proposal_id
        )
        assert response["Proposal"]["NetworkId"] == self.network_id
        assert response["Proposal"]["Status"] == "IN_PROGRESS"

        # Vote yes
        self.conn.vote_on_proposal(
            NetworkId=self.network_id,
            ProposalId=proposal_id,
            VoterMemberId=self.member_id,
            Vote="YES",
        )

        # Get the invitation
        response = self.conn.list_invitations()
        assert len(response["Invitations"]) == 2
        assert response["Invitations"][0]["NetworkSummary"]["Id"] == self.network_id
        assert response["Invitations"][0]["Status"] == "PENDING"
        assert response["Invitations"][1]["NetworkSummary"]["Id"] == self.network_id
        assert response["Invitations"][1]["Status"] == "PENDING"

    def test_reject_invitation(self):
        # Create proposal
        proposal_id = self.conn.create_proposal(
            NetworkId=self.network_id,
            MemberId=self.member_id,
            Actions=helpers.default_policy_actions,
        )["ProposalId"]

        # Get proposal details
        response = self.conn.get_proposal(
            NetworkId=self.network_id, ProposalId=proposal_id
        )
        assert response["Proposal"]["NetworkId"] == self.network_id
        assert response["Proposal"]["Status"] == "IN_PROGRESS"

        # Vote yes
        self.conn.vote_on_proposal(
            NetworkId=self.network_id,
            ProposalId=proposal_id,
            VoterMemberId=self.member_id,
            Vote="YES",
        )

        # Get the invitation
        response = self.conn.list_invitations()
        assert response["Invitations"][0]["NetworkSummary"]["Id"] == self.network_id
        assert response["Invitations"][0]["Status"] == "PENDING"
        invitation_id = response["Invitations"][0]["InvitationId"]

        # Reject - thanks but no thanks
        self.conn.reject_invitation(InvitationId=invitation_id)

        # Check the invitation status
        response = self.conn.list_invitations()
        assert response["Invitations"][0]["InvitationId"] == invitation_id
        assert response["Invitations"][0]["Status"] == "REJECTED"

    def test_reject_invitation_badinvitation(self):
        proposal_id = self.conn.create_proposal(
            NetworkId=self.network_id,
            MemberId=self.member_id,
            Actions=helpers.default_policy_actions,
        )["ProposalId"]

        self.conn.vote_on_proposal(
            NetworkId=self.network_id,
            ProposalId=proposal_id,
            VoterMemberId=self.member_id,
            Vote="YES",
        )

        with pytest.raises(ClientError) as ex:
            self.conn.reject_invitation(InvitationId="in-ABCDEFGHIJKLMNOP0123456789")
        err = ex.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert "InvitationId in-ABCDEFGHIJKLMNOP0123456789 not found." in err["Message"]
