"""Unit tests for networkfirewall-supported APIs."""

import boto3

from moto import mock_aws


@mock_aws
def test_create_firewall():
    client = boto3.client("network-firewall", region_name="us-east-1")
    firewall = client.create_firewall(
        FirewallName="test-firewall",
        FirewallPolicyArn="arn:aws:network-firewall:ap-southeast-1:123456789012:firewall-policy/test-policy",
        DeleteProtection=False,
        SubnetChangeProtection=False,
    )["Firewall"]

    assert firewall["FirewallName"] == "test-firewall"
    assert "FirewallArn" in firewall
    assert firewall["DeleteProtection"] is False
    assert firewall["SubnetChangeProtection"] is False
    assert firewall["FirewallPolicyChangeProtection"] is True


@mock_aws
def test_describe_logging_configuration():
    client = boto3.client("network-firewall", region_name="eu-west-1")
    firewall = client.create_firewall(
        FirewallName="test-firewall",
        FirewallPolicyArn="arn:aws:network-firewall:ap-southeast-1:123456789012:firewall-policy/test-policy",
    )["Firewall"]

    logging_config = {
        "LogDestinationConfigs": [
            {
                "LogDestinationType": "S3",
                "LogDestination": {
                    "bucketName": "DOC-EXAMPLE-BUCKET",
                    "prefix": "alerts",
                },
                "LogType": "FLOW",
            },
            {
                "LogDestinationType": "CloudWatchLogs",
                "LogDestination": {"logGroup": "alert-log-group"},
                "LogType": "ALERT",
            },
        ]
    }

    # Create a logging configuration
    client.update_logging_configuration(
        FirewallArn=firewall["FirewallArn"], LoggingConfiguration=logging_config
    )

    # Describe the logging configuration
    resp = client.describe_logging_configuration(FirewallArn=firewall["FirewallArn"])
    assert resp["FirewallArn"] == firewall["FirewallArn"]
    assert len(resp["LoggingConfiguration"]["LogDestinationConfigs"]) == 2
    log_dest_configs = resp["LoggingConfiguration"]["LogDestinationConfigs"]
    assert log_dest_configs[0]["LogDestinationType"] == "S3"
    assert log_dest_configs[0]["LogType"] == "FLOW"
    assert log_dest_configs[1]["LogDestinationType"] == "CloudWatchLogs"
    assert log_dest_configs[1]["LogType"] == "ALERT"


@mock_aws
def test_update_logging_configuration():
    client = boto3.client("network-firewall", region_name="ap-southeast-1")
    firewall = client.create_firewall(
        FirewallName="test-firewall",
        FirewallPolicyArn="arn:aws:network-firewall:ap-southeast-1:123456789012:firewall-policy/test-policy",
    )["Firewall"]

    logging_config = {
        "LogDestinationConfigs": [
            {
                "LogDestinationType": "S3",
                "LogDestination": {
                    "bucketName": "DOC-EXAMPLE-BUCKET",
                    "prefix": "alerts",
                },
                "LogType": "FLOW",
            }
        ]
    }

    resp = client.update_logging_configuration(
        FirewallArn=firewall["FirewallArn"], LoggingConfiguration=logging_config
    )
    assert resp["FirewallArn"] == firewall["FirewallArn"]
    assert resp["FirewallName"] == "test-firewall"
    assert len(resp["LoggingConfiguration"]["LogDestinationConfigs"]) == 1
    assert resp["LoggingConfiguration"] == logging_config


@mock_aws
def test_list_firewalls():
    client = boto3.client("network-firewall", region_name="ap-southeast-1")
    for i in range(5):
        client.create_firewall(
            FirewallName=f"test-firewall-{i}",
            FirewallPolicyArn="arn:aws:network-firewall:ap-southeast-1:123456789012:firewall-policy/test-policy",
            VpcId=f"vpc-1234567{i}",
        )

    # List all firewalls
    resp = client.list_firewalls()
    assert len(resp["Firewalls"]) == 5
    assert resp["Firewalls"][0]["FirewallName"] == "test-firewall-0"
    assert "FirewallArn" in resp["Firewalls"][0]

    # List firewalls with a specific VPC ID
    resp = client.list_firewalls(VpcIds=["vpc-12345671"])
    assert len(resp["Firewalls"]) == 1
    assert resp["Firewalls"][0]["FirewallName"] == "test-firewall-1"


@mock_aws
def test_describe_firewall():
    client = boto3.client("network-firewall", region_name="ap-southeast-1")
    firewall = client.create_firewall(
        FirewallName="test-firewall",
        FirewallPolicyArn="arn:aws:network-firewall:ap-southeast-1:123456789012:firewall-policy/test-policy",
        VpcId="vpc-12345678",
        SubnetMappings=[{"SubnetId": "subnet-12345678"}],
        DeleteProtection=False,
        SubnetChangeProtection=False,
        FirewallPolicyChangeProtection=False,
        Description="Test firewall",
        Tags=[{"Key": "Name", "Value": "test-firewall"}],
    )["Firewall"]

    # Describe the firewall using the ARN
    resp = client.describe_firewall(FirewallArn=firewall["FirewallArn"])
    assert resp["Firewall"]["FirewallName"] == "test-firewall"
    assert resp["Firewall"]["VpcId"] == "vpc-12345678"
    assert resp["Firewall"]["SubnetMappings"] == [{"SubnetId": "subnet-12345678"}]
    assert resp["Firewall"]["DeleteProtection"] is False
    assert resp["Firewall"]["SubnetChangeProtection"] is False
    assert resp["Firewall"]["FirewallPolicyChangeProtection"] is False
    assert resp["Firewall"]["Description"] == "Test firewall"
    assert resp["Firewall"]["Tags"] == [{"Key": "Name", "Value": "test-firewall"}]

    # Describe the firewall using the name
    resp_name = client.describe_firewall(FirewallName="test-firewall")
    assert resp_name["Firewall"]["FirewallName"] == "test-firewall"
