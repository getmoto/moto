import boto3
import pytest

from botocore.config import Config
from botocore.exceptions import ClientError
from moto import mock_managedblockchain
from . import helpers


@mock_managedblockchain
def test_create_node():
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

    # Create a node
    node_id = conn.create_node(
        NetworkId=network_id,
        MemberId=member_id,
        NodeConfiguration=helpers.default_nodeconfiguration,
    )["NodeId"]

    # Find node in full list
    nodes = conn.list_nodes(NetworkId=network_id, MemberId=member_id)["Nodes"]
    assert len(nodes) == 1
    assert helpers.node_id_exist_in_list(nodes, node_id) is True

    # Get node details
    response = conn.get_node(NetworkId=network_id, MemberId=member_id, NodeId=node_id)
    assert response["Node"]["AvailabilityZone"] == "us-east-1a"

    # Update node
    logconfignewenabled = not helpers.default_nodeconfiguration[
        "LogPublishingConfiguration"
    ]["Fabric"]["ChaincodeLogs"]["Cloudwatch"]["Enabled"]
    logconfignew = {
        "Fabric": {"ChaincodeLogs": {"Cloudwatch": {"Enabled": logconfignewenabled}}}
    }
    conn.update_node(
        NetworkId=network_id,
        MemberId=member_id,
        NodeId=node_id,
        LogPublishingConfiguration=logconfignew,
    )

    # Delete node
    conn.delete_node(NetworkId=network_id, MemberId=member_id, NodeId=node_id)

    # Find node in full list
    nodes = conn.list_nodes(NetworkId=network_id, MemberId=member_id)["Nodes"]
    assert len(nodes) == 1
    assert helpers.node_id_exist_in_list(nodes, node_id) is True

    # Find node in full list - only DELETED
    nodes = conn.list_nodes(NetworkId=network_id, MemberId=member_id, Status="DELETED")[
        "Nodes"
    ]
    assert len(nodes) == 1
    assert helpers.node_id_exist_in_list(nodes, node_id) is True

    # But cannot get
    with pytest.raises(ClientError) as ex:
        conn.get_node(NetworkId=network_id, MemberId=member_id, NodeId=node_id)
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Node {node_id} not found" in err["Message"]


@mock_managedblockchain
def test_create_node_standard_edition():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    frameworkconfiguration = {"Fabric": {"Edition": "STANDARD"}}

    response = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )
    network_id = response["NetworkId"]
    member_id = response["MemberId"]

    # Instance type only allowed with standard edition
    logconfigbad = dict(helpers.default_nodeconfiguration)
    logconfigbad["InstanceType"] = "bc.t3.large"
    node_id = conn.create_node(
        NetworkId=network_id, MemberId=member_id, NodeConfiguration=logconfigbad
    )["NodeId"]

    # Get node details
    response = conn.get_node(NetworkId=network_id, MemberId=member_id, NodeId=node_id)
    assert response["Node"]["InstanceType"] == "bc.t3.large"

    # Need another member so the network does not get deleted
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

    # Create the member
    conn.create_member(
        InvitationId=invitation_id,
        NetworkId=network_id,
        MemberConfiguration=helpers.create_member_configuration(
            "testmember2", "admin", "Admin12345", False, "Test Member 2"
        ),
    )

    # Remove  member 1 - should remove nodes
    conn.delete_member(NetworkId=network_id, MemberId=member_id)

    # Should now be an exception
    with pytest.raises(ClientError) as ex:
        conn.list_nodes(NetworkId=network_id, MemberId=member_id)
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Member {member_id} not found" in err["Message"]


@mock_managedblockchain
def test_create_too_many_nodes():
    # This test throws a ResourceLimitException, with HTTP status code 429
    # Boto3 automatically retries a request with that status code up to 5 times
    # Retrying is not going to make a difference to the output though...
    config = Config(retries={"max_attempts": 1, "mode": "standard"})
    conn = boto3.client("managedblockchain", region_name="us-east-1", config=config)

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

    # Create a node
    conn.create_node(
        NetworkId=network_id,
        MemberId=member_id,
        NodeConfiguration=helpers.default_nodeconfiguration,
    )

    # Create another node
    conn.create_node(
        NetworkId=network_id,
        MemberId=member_id,
        NodeConfiguration=helpers.default_nodeconfiguration,
    )

    # Find node in full list
    nodes = conn.list_nodes(NetworkId=network_id, MemberId=member_id)["Nodes"]
    assert len(nodes) == 2

    # Try to create one too many nodes
    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id,
            MemberId=member_id,
            NodeConfiguration=helpers.default_nodeconfiguration,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceLimitExceededException"
    assert f"Maximum number of nodes exceeded in member {member_id}" in err["Message"]


@mock_managedblockchain
def test_create_node_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeConfiguration=helpers.default_nodeconfiguration,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_create_node_badmember():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    network_id = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )["NetworkId"]

    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeConfiguration=helpers.default_nodeconfiguration,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_create_node_badnodeconfig():
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
    member_id = response["MemberId"]

    # Incorrect instance type
    logconfigbad = dict(helpers.default_nodeconfiguration)
    logconfigbad["InstanceType"] = "foo"
    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id, MemberId=member_id, NodeConfiguration=logconfigbad
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert "Requested instance foo isn't supported." in err["Message"]

    # Incorrect instance type for edition
    logconfigbad = dict(helpers.default_nodeconfiguration)
    logconfigbad["InstanceType"] = "bc.t3.large"
    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id, MemberId=member_id, NodeConfiguration=logconfigbad
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert (
        "Instance type bc.t3.large is not supported with STARTER Edition networks."
        in err["Message"]
    )

    # Incorrect availability zone
    logconfigbad = dict(helpers.default_nodeconfiguration)
    logconfigbad["AvailabilityZone"] = "us-east-11"
    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id, MemberId=member_id, NodeConfiguration=logconfigbad
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert "Availability Zone is not valid" in err["Message"]


@mock_managedblockchain
def test_list_nodes_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_nodes(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_list_nodes_badmember():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    network_id = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )["NetworkId"]

    with pytest.raises(ClientError) as ex:
        conn.list_nodes(NetworkId=network_id, MemberId="m-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_get_node_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_node(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_get_node_badmember():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    network_id = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )["NetworkId"]

    with pytest.raises(ClientError) as ex:
        conn.get_node(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_get_node_badnode():
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
    member_id = response["MemberId"]

    with pytest.raises(ClientError) as ex:
        conn.get_node(
            NetworkId=network_id,
            MemberId=member_id,
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Node nd-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_delete_node_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.delete_node(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_delete_node_badmember():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    network_id = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )["NetworkId"]

    with pytest.raises(ClientError) as ex:
        conn.delete_node(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_delete_node_badnode():
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
    member_id = response["MemberId"]

    with pytest.raises(ClientError) as ex:
        conn.delete_node(
            NetworkId=network_id,
            MemberId=member_id,
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Node nd-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_update_node_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.update_node(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
            LogPublishingConfiguration=helpers.default_nodeconfiguration[
                "LogPublishingConfiguration"
            ],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Network n-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_update_node_badmember():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    network_id = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )["NetworkId"]

    with pytest.raises(ClientError) as ex:
        conn.update_node(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
            LogPublishingConfiguration=helpers.default_nodeconfiguration[
                "LogPublishingConfiguration"
            ],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Member m-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]


@mock_managedblockchain
def test_update_node_badnode():
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
    member_id = response["MemberId"]

    with pytest.raises(ClientError) as ex:
        conn.update_node(
            NetworkId=network_id,
            MemberId=member_id,
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
            LogPublishingConfiguration=helpers.default_nodeconfiguration[
                "LogPublishingConfiguration"
            ],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Node nd-ABCDEFGHIJKLMNOP0123456789 not found" in err["Message"]
