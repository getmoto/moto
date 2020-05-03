from __future__ import unicode_literals

import boto3
import sure  # noqa

from moto import mock_managedblockchain


@mock_managedblockchain
def test_create_network():
    conn = boto3.client("managedblockchain", region_name="us-east-1")

    frameworkconfiguration = {"Fabric": {"Edition": "STARTER"}}

    votingpolicy = {
        "ApprovalThresholdPolicy": {
            "ThresholdPercentage": 50,
            "ProposalDurationInHours": 24,
            "ThresholdComparator": "GREATER_THAN_OR_EQUAL_TO",
        }
    }

    memberconfiguration = {
        "Name": "testmember1",
        "Description": "Test Member 1",
        "FrameworkConfiguration": {
            "Fabric": {"AdminUsername": "admin", "AdminPassword": "Admin12345"}
        },
        "LogPublishingConfiguration": {
            "Fabric": {"CaLogs": {"Cloudwatch": {"Enabled": False}}}
        },
    }

    conn.create_network(
        Name="testnetwork1",
        Description="Test Network 1",
        Framework="HYPERLEDGER_FABRIC",
        FrameworkVersion="1.2",
        FrameworkConfiguration=frameworkconfiguration,
        VotingPolicy=votingpolicy,
        MemberConfiguration=memberconfiguration,
    )

    # Find in full list
    response = conn.list_networks()
    mbcnetworks = response["Networks"]
    mbcnetworks.should.have.length_of(1)
    mbcnetworks[0]["Name"].should.equal("testnetwork1")

    # Get network details
    network_id = mbcnetworks[0]["Id"]
    response = conn.get_network(NetworkId=network_id)
    response["Network"]["Name"].should.equal("testnetwork1")
