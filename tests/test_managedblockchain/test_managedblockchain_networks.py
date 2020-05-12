from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto.managedblockchain.exceptions import BadRequestException
from moto import mock_managedblockchain


default_frameworkconfiguration = {"Fabric": {"Edition": "STARTER"}}

default_votingpolicy = {
    "ApprovalThresholdPolicy": {
        "ThresholdPercentage": 50,
        "ProposalDurationInHours": 24,
        "ThresholdComparator": "GREATER_THAN_OR_EQUAL_TO",
    }
}

default_memberconfiguration = {
    "Name": "testmember1",
    "Description": "Test Member 1",
    "FrameworkConfiguration": {
        "Fabric": {"AdminUsername": "admin", "AdminPassword": "Admin12345"}
    },
    "LogPublishingConfiguration": {
        "Fabric": {"CaLogs": {"Cloudwatch": {"Enabled": False}}}
    },
}


@mock_managedblockchain
def test_create_network():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    response = conn.create_network(
        Name="testnetwork1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=default_frameworkconfiguration,
        VotingPolicy=default_votingpolicy,
        MemberConfiguration=default_memberconfiguration,
    )
    response["NetworkId"].should.match("n-[A-Z0-9]{26}")
    response["MemberId"].should.match("m-[A-Z0-9]{26}")

    # Find in full list
    response = conn.list_networks()
    mbcnetworks = response["Networks"]
    mbcnetworks.should.have.length_of(1)
    mbcnetworks[0]["Name"].should.equal("testnetwork1")

    # Get network details
    network_id = mbcnetworks[0]["Id"]
    response = conn.get_network(NetworkId=network_id)
    response["Network"]["Name"].should.equal("testnetwork1")


@mock_managedblockchain
def test_create_network_withopts():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    response = conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=default_frameworkconfiguration,
        VotingPolicy=default_votingpolicy,
        MemberConfiguration=default_memberconfiguration,
    )
    response["NetworkId"].should.match("n-[A-Z0-9]{26}")
    response["MemberId"].should.match("m-[A-Z0-9]{26}")

    # Find in full list
    response = conn.list_networks()
    mbcnetworks = response["Networks"]
    mbcnetworks.should.have.length_of(1)
    mbcnetworks[0]["Description"].should.equal("Test Network 1")

    # Get network details
    network_id = mbcnetworks[0]["Id"]
    response = conn.get_network(NetworkId=network_id)
    response["Network"]["Description"].should.equal("Test Network 1")


@mock_managedblockchain
def test_create_network_noframework():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    response = conn.create_network.when.called_with(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_VINYL",
        FrameworkVersion="1.2",
        FrameworkConfiguration=default_frameworkconfiguration,
        VotingPolicy=default_votingpolicy,
        MemberConfiguration=default_memberconfiguration,
    ).should.throw(Exception, "Invalid request body")


@mock_managedblockchain
def test_create_network_badframeworkver():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    response = conn.create_network.when.called_with(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.X",
        FrameworkConfiguration=default_frameworkconfiguration,
        VotingPolicy=default_votingpolicy,
        MemberConfiguration=default_memberconfiguration,
    ).should.throw(
        Exception, "Invalid version 1.X requested for framework HYPERLEDGER_FABRIC"
    )


@mock_managedblockchain
def test_create_network_badedition():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    frameworkconfiguration = {"Fabric": {"Edition": "SUPER"}}

    response = conn.create_network.when.called_with(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=frameworkconfiguration,
        VotingPolicy=default_votingpolicy,
        MemberConfiguration=default_memberconfiguration,
    ).should.throw(Exception, "Invalid request body")


@mock_managedblockchain
def test_get_network_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    response = conn.get_network.when.called_with(
        NetworkId="n-BADNETWORK",
    ).should.throw(Exception, "Network n-BADNETWORK not found")
