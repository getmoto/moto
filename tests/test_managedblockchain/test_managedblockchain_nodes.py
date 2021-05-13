from __future__ import unicode_literals

import boto3
import pytest
import sure  # noqa

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
    response = conn.create_node(
        NetworkId=network_id,
        MemberId=member_id,
        NodeConfiguration=helpers.default_nodeconfiguration,
    )
    node_id = response["NodeId"]

    # Find node in full list
    response = conn.list_nodes(NetworkId=network_id, MemberId=member_id)
    nodes = response["Nodes"]
    nodes.should.have.length_of(1)
    helpers.node_id_exist_in_list(nodes, node_id).should.equal(True)

    # Get node details
    response = conn.get_node(NetworkId=network_id, MemberId=member_id, NodeId=node_id)
    response["Node"]["AvailabilityZone"].should.equal("us-east-1a")

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
    conn.delete_node(
        NetworkId=network_id, MemberId=member_id, NodeId=node_id,
    )

    # Find node in full list
    response = conn.list_nodes(NetworkId=network_id, MemberId=member_id)
    nodes = response["Nodes"]
    nodes.should.have.length_of(1)
    helpers.node_id_exist_in_list(nodes, node_id).should.equal(True)

    # Find node in full list - only DELETED
    response = conn.list_nodes(
        NetworkId=network_id, MemberId=member_id, Status="DELETED"
    )
    nodes = response["Nodes"]
    nodes.should.have.length_of(1)
    helpers.node_id_exist_in_list(nodes, node_id).should.equal(True)

    # But cannot get
    with pytest.raises(ClientError) as ex:
        conn.get_node(NetworkId=network_id, MemberId=member_id, NodeId=node_id)
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Node {0} not found".format(node_id))


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
    response = conn.create_node(
        NetworkId=network_id, MemberId=member_id, NodeConfiguration=logconfigbad,
    )
    node_id = response["NodeId"]

    # Get node details
    response = conn.get_node(NetworkId=network_id, MemberId=member_id, NodeId=node_id)
    response["Node"]["InstanceType"].should.equal("bc.t3.large")

    # Need another member so the network does not get deleted
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

    # Create the member
    response = conn.create_member(
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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member {0} not found".format(member_id))


@mock_managedblockchain
def test_create_too_many_nodes():
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
    response = conn.create_node(
        NetworkId=network_id,
        MemberId=member_id,
        NodeConfiguration=helpers.default_nodeconfiguration,
    )

    # Create another node
    response = conn.create_node(
        NetworkId=network_id,
        MemberId=member_id,
        NodeConfiguration=helpers.default_nodeconfiguration,
    )

    # Find node in full list
    response = conn.list_nodes(NetworkId=network_id, MemberId=member_id)
    nodes = response["Nodes"]
    nodes.should.have.length_of(2)

    # Try to create one too many nodes
    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id,
            MemberId=member_id,
            NodeConfiguration=helpers.default_nodeconfiguration,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceLimitExceededException")
    err["Message"].should.contain(
        "Maximum number of nodes exceeded in member {0}".format(member_id)
    )


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_create_node_badmember():
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

    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeConfiguration=helpers.default_nodeconfiguration,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


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
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.contain("Requested instance foo isn't supported.")

    # Incorrect instance type for edition
    logconfigbad = dict(helpers.default_nodeconfiguration)
    logconfigbad["InstanceType"] = "bc.t3.large"
    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id, MemberId=member_id, NodeConfiguration=logconfigbad
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.contain(
        "Instance type bc.t3.large is not supported with STARTER Edition networks."
    )

    # Incorrect availability zone
    logconfigbad = dict(helpers.default_nodeconfiguration)
    logconfigbad["AvailabilityZone"] = "us-east-11"
    with pytest.raises(ClientError) as ex:
        conn.create_node(
            NetworkId=network_id, MemberId=member_id, NodeConfiguration=logconfigbad
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.contain("Availability Zone is not valid")


@mock_managedblockchain
def test_list_nodes_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.list_nodes(
            NetworkId="n-ABCDEFGHIJKLMNOP0123456789",
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_list_nodes_badmember():
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

    with pytest.raises(ClientError) as ex:
        conn.list_nodes(
            NetworkId=network_id, MemberId="m-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_get_node_badmember():
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

    with pytest.raises(ClientError) as ex:
        conn.get_node(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Node nd-ABCDEFGHIJKLMNOP0123456789 not found")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_delete_node_badmember():
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

    with pytest.raises(ClientError) as ex:
        conn.delete_node(
            NetworkId=network_id,
            MemberId="m-ABCDEFGHIJKLMNOP0123456789",
            NodeId="nd-ABCDEFGHIJKLMNOP0123456789",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Node nd-ABCDEFGHIJKLMNOP0123456789 not found")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")


@mock_managedblockchain
def test_update_node_badmember():
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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Member m-ABCDEFGHIJKLMNOP0123456789 not found")


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
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Node nd-ABCDEFGHIJKLMNOP0123456789 not found")
