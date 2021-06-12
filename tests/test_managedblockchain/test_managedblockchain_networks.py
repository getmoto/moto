from __future__ import unicode_literals

import boto3
import pytest
import sure  # noqa

from botocore.exceptions import ClientError
from moto import mock_managedblockchain
from . import helpers


@mock_managedblockchain
def test_create_network():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

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
    network_id.should.match("n-[A-Z0-9]{26}")
    member_id.should.match("m-[A-Z0-9]{26}")

    # Find in full list
    response = conn.list_networks()
    mbcnetworks = response["Networks"]
    mbcnetworks.should.have.length_of(1)
    mbcnetworks[0]["Name"].should.equal("testnetwork1")

    # Get network details
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
        FrameworkConfiguration=helpers.default_frameworkconfiguration,
        VotingPolicy=helpers.default_votingpolicy,
        MemberConfiguration=helpers.default_memberconfiguration,
    )
    network_id = response["NetworkId"]
    member_id = response["MemberId"]
    network_id.should.match("n-[A-Z0-9]{26}")
    member_id.should.match("m-[A-Z0-9]{26}")

    # Find in full list
    response = conn.list_networks()
    mbcnetworks = response["Networks"]
    mbcnetworks.should.have.length_of(1)
    mbcnetworks[0]["Description"].should.equal("Test Network 1")

    # Get network details
    response = conn.get_network(NetworkId=network_id)
    response["Network"]["Description"].should.equal("Test Network 1")


@mock_managedblockchain
def test_create_network_noframework():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.create_network(
            Name="testnetwork1",
            Description="Test Network 1",
            Framework="HYPERLEDGER_VINYL",
            FrameworkVersion="1.2",
            FrameworkConfiguration=helpers.default_frameworkconfiguration,
            VotingPolicy=helpers.default_votingpolicy,
            MemberConfiguration=helpers.default_memberconfiguration,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain("Invalid request body")


@mock_managedblockchain
def test_create_network_badframeworkver():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.create_network(
            Name="testnetwork1",
            Description="Test Network 1",
            Framework="HYPERLEDGER_FABRIC",
            FrameworkVersion="1.X",
            FrameworkConfiguration=helpers.default_frameworkconfiguration,
            VotingPolicy=helpers.default_votingpolicy,
            MemberConfiguration=helpers.default_memberconfiguration,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain(
        "Invalid version 1.X requested for framework HYPERLEDGER_FABRIC"
    )


@mock_managedblockchain
def test_create_network_badedition():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    frameworkconfiguration = {"Fabric": {"Edition": "SUPER"}}

    with pytest.raises(ClientError) as ex:
        conn.create_network(
            Name="testnetwork1",
            Description="Test Network 1",
            Framework="HYPERLEDGER_FABRIC",
            FrameworkVersion="1.2",
            FrameworkConfiguration=frameworkconfiguration,
            VotingPolicy=helpers.default_votingpolicy,
            MemberConfiguration=helpers.default_memberconfiguration,
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("BadRequestException")
    err["Message"].should.contain("Invalid request body")


@mock_managedblockchain
def test_get_network_badnetwork():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        conn.get_network(NetworkId="n-ABCDEFGHIJKLMNOP0123456789")
    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.contain("Network n-ABCDEFGHIJKLMNOP0123456789 not found")
