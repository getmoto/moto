import boto3
import pytest
from botocore.config import Config
from botocore.exceptions import ClientError, ParamValidationError

from moto import mock_aws

from . import helpers


@mock_aws
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

    # Create the member
    member_id2 = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False
        ),
    )["MemberId"]

    # Check the invitation status
    response = conn.list_invitations()
    assert response["Invitations"][0]["InvitationId"] == invitation_id
    assert response["Invitations"][0]["Status"] == "ACCEPTED"

    # Find member in full list
    members = conn.list_members(NetworkId=network_id)["Members"]
    assert len(members) == 2
    assert helpers.member_id_exist_in_list(members, member_id2) is True

    # Get member 2 details
    response = conn.get_member(NetworkId=network_id, MemberId=member_id2)
    assert response["Member"]["Name"] == "testmember2"

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
    cloudwatch = response["Member"]["LogPublishingConfiguration"]["Fabric"]["CaLogs"][
        "Cloudwatch"
    ]
    assert cloudwatch["Enabled"] == logconfignewenabled


@mock_aws
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

    # Create the member
    member_id2 = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False, "Test Member 2"
        ),
    )["MemberId"]

    # Check the invitation status
    response = conn.list_invitations()
    assert response["Invitations"][0]["InvitationId"] == invitation_id
    assert response["Invitations"][0]["Status"] == "ACCEPTED"

    # Find member in full list
    members = conn.list_members(NetworkId=network_id)["Members"]
    assert len(members) == 2
    assert helpers.member_id_exist_in_list(members, member_id2) is True

    # Get member 2 details
    response = conn.get_member(NetworkId=network_id, MemberId=member_id2)
    assert response["Member"]["Description"] == "Test Member 2"

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
    assert err["Code"] == "InvalidRequestException"
    assert f"Invitation {invitation_id} not valid" in err["Message"]

    # Delete member 2
    conn.delete_member(NetworkId=network_id, MemberId=member_id2)

    # Member is still in the list
    members = conn.list_members(NetworkId=network_id)["Members"]
    assert len(members) == 2

    # But cannot get
    with pytest.raises(ClientError) as ex:
        conn.get_member(NetworkId=network_id, MemberId=member_id2)
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Member {member_id2} not found" in err["Message"]

    # Delete member 1
    conn.delete_member(NetworkId=network_id, MemberId=member_id)

    # Network should be gone
    mbcnetworks = conn.list_networks()["Networks"]
    assert len(mbcnetworks) == 0

    # Verify the invitation network status is DELETED
    # Get the invitation
    response = conn.list_invitations()
    assert len(response["Invitations"]) == 1
    assert response["Invitations"][0]["NetworkSummary"]["Id"] == network_id
    assert response["Invitations"][0]["NetworkSummary"]["Status"] == "DELETED"


@mock_aws
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
    proposal_id = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )["ProposalId"]

    # Vote yes
    conn.vote_on_proposal(
        NetworkId=network_id,
        ProposalId=proposal_id,
        VoterMemberId=member_id,
        Vote="YES",
    )

    # Get the invitation
    response = conn.list_invitations()
    invitation_id = response["Invitations"][0]["InvitationId"]

    # Create the member
    member_id2 = conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False, "Test Member 2"
        ),
    )["MemberId"]

    both_policy_actions = {
        "Invitations": [{"Principal": "123456789012"}],
        "Removals": [{"MemberId": member_id2}],
    }

    # Create proposal (invite and remove member)
    proposal_id2 = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=both_policy_actions
    )["ProposalId"]

    # Get proposal details
    response = conn.get_proposal(NetworkId=network_id, ProposalId=proposal_id2)
    assert response["Proposal"]["NetworkId"] == network_id
    assert response["Proposal"]["Status"] == "IN_PROGRESS"

    # Vote yes
    conn.vote_on_proposal(
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
    assert len(invitations) == 1

    # Member is still in the list
    members = conn.list_members(NetworkId=network_id)["Members"]
    assert len(members) == 2
    foundmember2 = False
    for member in members:
        if member["Id"] == member_id2 and member["Status"] == "DELETED":
            foundmember2 = True
    assert foundmember2 is True


@mock_aws
def test_create_too_many_members():
    # This test throws a ResourceLimitException, with HTTP status code 429
    # Boto3 automatically retries a request with that status code up to 5 times
    # Retrying is not going to make a difference to the output though...
    config = Config(retries={"max_attempts": 1, "mode": "standard"})
    conn = boto3.client("managedblockchain", region_name="us-east-1", config=config)

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
        proposal_id = conn.create_proposal(
            NetworkId=network_id,
            MemberId=member_id,
            Actions=helpers.default_policy_actions,
        )["ProposalId"]

        # Vote yes
        conn.vote_on_proposal(
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
        members = conn.list_members(NetworkId=network_id)["Members"]
        assert len(members) == counter
        assert helpers.member_id_exist_in_list(members, member_id) is True

        # Get member details
        response = conn.get_member(NetworkId=network_id, MemberId=member_id)
        assert response["Member"]["Description"] == "Test Member " + str(counter)

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
    assert err["Code"] == "ResourceLimitExceededException"
    assert "is the maximum number of members allowed in a" in err["Message"]


@mock_aws
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
    proposal_id = conn.create_proposal(
        NetworkId=network_id, MemberId=member_id, Actions=helpers.default_policy_actions
    )["ProposalId"]

    # Vote yes
    conn.vote_on_proposal(
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
    assert err["Code"] == "InvalidRequestException"
    assert (
        f"Member name testmember1 already exists in network {network_id}"
        in err["Message"]
    )


@mock_aws
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
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_aws
def test_create_another_member_badinvitation():
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
        conn.create_member(
            NetworkId=network_id,
            InvitationId="in-ABCDEFGHIJKLMNOP0123456789",
            MemberConfiguration=helpers.create_member_configuration(
                "testmember2", "admin", "Admin12345", False
            ),
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert "Invitation in-ABCDEFGHIJKLMNOP0123456789 not valid" in err["Message"]


@mock_aws
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
    invitation_id = response["Invitations"][0]["InvitationId"]

    badadminpassmemberconf = helpers.create_member_configuration(
        "testmember2", "admin", "Admin12345", False
    )

    # Too short
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"]["AdminPassword"] = (
        "badap"
    )
    with pytest.raises(ParamValidationError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value
    assert (
        "Invalid length for parameter MemberConfiguration.FrameworkConfiguration.Fabric.AdminPassword"
        in str(err)
    )

    # No uppercase or numbers
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"]["AdminPassword"] = (
        "badadminpwd"
    )
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert "Invalid request body" in err["Message"]

    # No lowercase or numbers
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"]["AdminPassword"] = (
        "BADADMINPWD"
    )
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert "Invalid request body" in err["Message"]

    # No numbers
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"]["AdminPassword"] = (
        "badAdminpwd"
    )
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert "Invalid request body" in err["Message"]

    # Invalid character
    badadminpassmemberconf["FrameworkConfiguration"]["Fabric"]["AdminPassword"] = (
        "badAdmin@pwd1"
    )
    with pytest.raises(ClientError) as ex:
        conn.create_member(
            NetworkId=network_id,
            InvitationId=invitation_id,
            MemberConfiguration=badadminpassmemberconf,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "BadRequestException"
    assert "Invalid request body" in err["Message"]


@mock_aws
def test_list_members_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_members(NetworkId="n-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_aws
def test_get_member_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_member(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_aws
def test_get_member_badmember():
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
        conn.get_member(NetworkId=network_id, MemberId="m-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_aws
def test_delete_member_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.delete_member(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_aws
def test_delete_member_badmember():
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
        conn.delete_member(
            NetworkId=network_id, MemberId="m-ABCDEFGHIJKLMNOP0123456789"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_aws
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
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_aws
def test_update_member_badmember():
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
        conn.update_member(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            LogPublishingConfiguration=helpers.default_memberconfiguration[
                "LogPublishingConfiguration"
            ],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]
