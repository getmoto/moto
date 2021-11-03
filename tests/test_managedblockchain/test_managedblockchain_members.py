import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError, ParamValidationError
from moto import mock_managedblockchain
from . import helpers


@mock_managedblockchain
def test_create_another_member():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Create network
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

    # Create the member
    response = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False
        ),
    )
    member_id2 = response["MemberId"]

    # Check the invitation status
    response = conn.list_invitations()
    response["Invitations"][0]["InvitationId"].should.equal(invitation_id)
    response["Invitations"][0]["Status"].should.equal("ACCEPTED")

    # Find member in full list
    response = conn.list_members(NetworkId=network_id)
    members = response["Members"]
    members.should.have.length_of(2)
    helpers.member_id_exist_in_list(members, member_id2).should.equal(True)

    # Get member 2 details
    response = conn.get_member(NetworkId=network_id, MemberId=member_id2)
    response["Member"]["Name"].should.equal("testmember2")

    # Update member
    logconfignewenabled = not helpers.default_memberconfiguration[
        "LogPublishingConfiguration"
    ]["Fabric"]["CaLogs"]["Cloudwatch"]["Enabled"]
    logconfignew = {
        "Fabric": {"CaLogs": {"Cloudwatch": {"Enabled": logconfignewenabled}}}
    }
    conn.update_member(
        NetworkId=network_id,
        MemberId=member_id2,
        LogPublishingConfiguration=logconfignew,
    )

    # Get member 2 details
    response = conn.get_member(NetworkId=network_id, MemberId=member_id2)
    response["Member"]["LogPublishingConfiguration"]["Fabric"]["CaLogs"]["Cloudwatch"][
        "Enabled"
    ].should.equal(logconfignewenabled)


@mock_managedblockchain
def test_create_another_member_withopts():
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

    # Create the member
    response = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False, "Test Member 2"
        ),
    )
    member_id2 = response["MemberId"]

    # Check the invitation status
    response = conn.list_invitations()
    response["Invitations"][0]["InvitationId"].should.equal(invitation_id)
    response["Invitations"][0]["Status"].should.equal("ACCEPTED")

    # Find member in full list
    response = conn.list_members(NetworkId=network_id)
    members = response["Members"]
    members.should.have.length_of(2)
    helpers.member_id_exist_in_list(members, member_id2).should.equal(True)

    # Get member 2 details
    response = conn.get_member(NetworkId=network_id, MemberId=member_id2)
    response["Member"]["Description"].should.equal("Test Member 2")

    # Try to create member with already used invitation
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            InvitationId=invitation_id,
            NetworkId=network_id,
            MemberConfiguration=helpers.create_member_configuration(
                "testmember2", "admin", "Admin12345", False, "Test Member 2 Duplicate"
            ),
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.contain("Invitation {0} not valid".format(invitation_id))

    # Delete member 2
    conn.delete_member(NetworkId=network_id, MemberId=member_id2)

    # Member is still in the list
    response = conn.list_members(NetworkId=network_id)
    members = response["Members"]
    members.should.have.length_of(2)

    # But cannot get
    with pytest.raises(ClientError) as ex:
        conn.get_member(NetworkId=network_id, MemberId=member_id2)
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member {0} not found".format(member_id2))

    # Delete member 1
    conn.delete_member(NetworkId=network_id, MemberId=member_id)

    # Network should be gone
    response = conn.list_networks()
    mbcnetworks = response["Networks"]
    mbcnetworks.should.have.length_of(0)

    # Verify the invitation network status is DELETED
    # Get the invitation
    response = conn.list_invitations()
    response["Invitations"].should.have.length_of(1)
    response["Invitations"][0]["NetworkSummary"]["Id"].should.equal(network_id)
    response["Invitations"][0]["NetworkSummary"]["Status"].should.equal("DELETED")


@mock_managedblockchain
def test_invite_and_remove_member():
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

    # Create proposal (create additional member)
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

    both_policy_actions = {
        "Invitations": [{"Principal": "123456789012"}],
        "Removals": [{"MemberId": member_id2}],
    }

    # Create proposal (invite and remove member)
    response = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=both_policy_actions,
    )
    proposal_id2 = response["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id2)
    response["Proposal"]["NetworkId"].should.equal(network_id)
    response["Proposal"]["Status"].should.equal("IN_PROGRESS")

    # Vote yes
    response = conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id2,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Check the invitation status
    response = conn.list_invitations()
    invitations = helpers.select_invitation_id_for_network(
        response["Invitations"], network_id, "PENDING"
    )
    invitations.should.have.length_of(1)

    # Member is still in the list
    response = conn.list_members(NetworkId=network_id)
    members = response["Members"]
    members.should.have.length_of(2)
    foundmember2 = False
    for member in members:
        if member["Id"] == member_id2 and member["Status"] == "DELETED":
            foundmember2 = True
    foundmember2.should.equal(True)


@mock_managedblockchain
def test_create_too_many_members():
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

    # Create 4 more members - create invitations for 5
    for counter in range(2, 7):
        # Create proposal
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

    for counter in range(2, 6):
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

        # Find member in full list
        response = conn.list_members(NetworkId=network_id)
        members = response["Members"]
        members.should.have.length_of(counter)
        helpers.member_id_exist_in_list(members, member_id).should.equal(True)

        # Get member details
        response = conn.get_member(NetworkId=network_id, MemberId=member_id)
        response["Member"]["Description"].should.equal("Test Member " + str(counter))

    # Try to create the sixth
    response = conn.list_invitations()
    invitation_id = helpers.select_invitation_id_for_network(
        response["Invitations"], network_id, "PENDING"
    )[0]

    # Try to create one too many members
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            InvitationId=invitation_id,
            NetworkId=network_id,
            MemberConfiguration=helpers.create_member_configuration(
                "testmember6", "admin", "Admin12345", False, "Test Member 6"
            ),
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceLimitExceededException")
    err["Message"].should.contain("is the maximum number of members allowed in a")


@mock_managedblockchain
def test_create_another_member_alreadyhave():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    # Create network
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
    member_id = response["MemberId"]

    # Create proposal
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

    # Get the invitation
    response = conn.list_invitations()
    invitation_id = response["Invitations"][0]["InvitationId"]

    # Should fail trying to create with same name
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=helpers.create_member_configuration(
                "testmember1", "admin", "Admin12345", False
            ),
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.contain(
        "Member name {0} already exists in network {1}".format(
            "testmember1", network_id
        )
    )


@mock_managedblockchain
def test_create_another_member_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            InvitationId="id-ABCDEFGHIJKLMNOP0123456789",
            MemberConfiguration=helpers.create_member_configuration(
                "testmember2", "admin", "Admin12345", False
            ),
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_create_another_member_badinvitation():
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
        conn.create_member(
            NetworkId=network_id,
            InvitationId="in-ABCDEFGHIJKLMNOP0123456789",
            MemberConfiguration=helpers.create_member_configuration(
                "testmember2", "admin", "Admin12345", False
            ),
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.contain("Invitation in-ABCDEFGHIJKLMNOP0123456789 not valid")


@mock_managedblockchain
def test_create_another_member_adminpassword():
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
    invitation_id = response["Invitations"][0]["InvitationId"]

    badadminpassmemberconf = helpers.create_member_configuration(
        "testmember2", "admin", "Admin12345", False
    )

    # Too short
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"][
        "AdminPassword"
    ] = "badap"
    with pytest.raises(ParamValidationError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value
    str(err).should.contain(
        "Invalid length for parameter MemberConfiguration.FrameworkConfiguration.Fabric.AdminPassword"
    )

    # No uppercase or numbers
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"][
        "AdminPassword"
    ] = "badadminpwd"
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain("Invalid request body")

    # No lowercase or numbers
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"][
        "AdminPassword"
    ] = "BADADMINPWD"
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain("Invalid request body")

    # No numbers
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"][
        "AdminPassword"
    ] = "badAdminpwd"
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain("Invalid request body")

    # Invalid character
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"][
        "AdminPassword"
    ] = "badAdmin@pwd1"
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain("Invalid request body")


@mock_managedblockchain
def test_list_members_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_members(NetworkId="n-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_get_member_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_member(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_get_member_badmember():
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
        conn.get_member(NetworkId=network_id, MemberId="m-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_delete_member_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.delete_member(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_delete_member_badmember():
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
        conn.delete_member(
            NetworkId=network_id, MemberId="m-ABCDEFGHIJKLMNOP0123456789"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_update_member_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.update_member(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            LogPublishingConfiguration=helpers.default_memberconfiguration[
                "LogPublishingConfiguration"
            ],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_update_member_badmember():
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
        conn.update_member(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            LogPublishingConfiguration=helpers.default_memberconfiguration[
                "LogPublishingConfiguration"
            ],
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")
