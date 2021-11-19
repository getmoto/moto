"""Unit tests for route53resolver rule-related APIs."""
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

import pytest

from moto import mock_route53resolver
from moto import settings
from moto.core import ACCOUNT_ID
from moto.core.utils import get_random_hex
from moto.ec2 import mock_ec2

from .test_route53resolver_endpoint import TEST_REGION, create_test_endpoint

TEST_REGION = "us-east-1" if settings.TEST_SERVER_MODE else "us-west-2"


def create_test_rule(client, tags=None):
    """Create an rule that can be used for testing purposes.

    Can't be used for unit tests that need to know/test the arguments.
    """
    if not tags:
        tags = []
    random_num = get_random_hex(10)

    resolver_rule = client.create_resolver_rule(
        CreatorRequestId=random_num,
        Name="X" + random_num,
        RuleType="FORWARD",
        DomainName=f"X{random_num}.com",
        TargetIps=[
            {"Ip": "10.0.1.200", "Port": 123},
            {"Ip": "10.0.0.20", "Port": 456},
        ],
        # ResolverEndpointId=random_num -- will test this separately
        Tags=tags,
    )
    return resolver_rule["ResolverRule"]


@mock_route53resolver
def test_route53resolver_invalid_create_rule_args():
    """Test invalid arguments to the create_resolver_rule API."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    random_num = get_random_hex(10)

    # Verify ValidationException error messages are accumulated properly:
    #  - creator requestor ID that exceeds the allowed length of 255.
    #  - name that exceeds the allowed length of 64.
    #  - rule_type that's not FORWARD, SYSTEM or RECURSIVE.
    #  - domain_name that exceeds the allowed length of 256.
    long_id = random_num * 25 + "123456"
    long_name = random_num * 6 + "abcde"
    bad_rule_type = "foo"
    long_domain_name = "bar" * 86
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=long_id,
            Name=long_name,
            RuleType=bad_rule_type,
            DomainName=long_domain_name,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "4 validation errors detected" in err["Message"]
    assert (
        f"Value '{long_id}' at 'creatorRequestId' failed to satisfy constraint: "
        f"Member must have length less than or equal to 255"
    ) in err["Message"]
    assert (
        f"Value '{long_name}' at 'name' failed to satisfy constraint: "
        f"Member must have length less than or equal to 64"
    ) in err["Message"]
    assert (
        f"Value '{bad_rule_type}' at 'ruleType' failed to satisfy constraint: "
        f"Member must satisfy enum value set: [FORWARD, SYSTEM, RECURSIVE]"
    ) in err["Message"]
    assert (
        f"Value '{long_domain_name}' at 'domainName' failed to satisfy "
        f"constraint: Member must have length less than or equal to 256"
    ) in err["Message"]

    # Some single ValidationException errors ...
    bad_target_ips = [
        {"Ip": "10.1.0.22", "Port": 5},
        {"Ip": "10.1.0.23", "Port": 700000},
        {"Ip": "10.1.0.24", "Port": 70},
    ]
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=random_num,
            Name="A" + random_num,
            RuleType="FORWARD",
            DomainName=f"{random_num}.com",
            TargetIps=bad_target_ips,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{bad_target_ips[1]}' at 'targetIps.port' failed to "
        f"satisfy constraint: Member must have value less than or equal to "
        f"65535"
    ) in err["Message"]

    too_long_resolver_endpoint_id = "foo" * 25
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=random_num,
            Name="A" + random_num,
            RuleType="FORWARD",
            DomainName=f"{random_num}.com",
            ResolverEndpointId=too_long_resolver_endpoint_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{too_long_resolver_endpoint_id}' at 'resolverEndpointId' "
        f"failed to satisfy constraint: Member must have length less than or "
        f"equal to 64"
    ) in err["Message"]


@mock_ec2
@mock_route53resolver
def test_route53resolver_create_resolver_rule():  # pylint: disable=too-many-locals
    """Test good create_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    random_num = get_random_hex(10)

    # Create a good endpoint that we can use to test.
    created_endpoint = create_test_endpoint(client, ec2_client)
    endpoint_id = created_endpoint["Id"]

    creator_request_id = random_num
    name = "X" + random_num
    domain_name = f"{random_num}.test"
    target_ips = [{"Ip": "1.2.3.4", "Port": 5}]
    response = client.create_resolver_rule(
        CreatorRequestId=creator_request_id,
        Name=name,
        RuleType="FORWARD",
        DomainName=domain_name,
        TargetIps=target_ips,
        ResolverEndpointId=endpoint_id,
    )
    rule = response["ResolverRule"]
    id_value = rule["Id"]
    assert id_value.startswith("rslvr-rr-")
    assert rule["CreatorRequestId"] == creator_request_id
    assert (
        rule["Arn"]
        == f"arn:aws:route53resolver:{TEST_REGION}:{ACCOUNT_ID}:resolver-rule/{id_value}"
    )
    assert rule["DomainName"] == domain_name
    assert rule["Status"] == "COMPLETE"
    assert "Successfully created Resolver Rule" in rule["StatusMessage"]
    assert rule["RuleType"] == "FORWARD"
    assert rule["Name"] == name
    assert len(rule["TargetIps"]) == 1
    assert rule["TargetIps"][0]["Ip"] == target_ips[0]["Ip"]
    assert rule["TargetIps"][0]["Port"] == target_ips[0]["Port"]
    assert rule["ResolverEndpointId"] == endpoint_id
    assert rule["OwnerId"] == ACCOUNT_ID
    assert rule["ShareStatus"] == "SHARED_WITH_ME"

    time_format = "%Y-%m-%dT%H:%M:%S.%f+00:00"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    creation_time = datetime.strptime(rule["CreationTime"], time_format)
    creation_time = creation_time.replace(tzinfo=None)
    assert creation_time <= now

    modification_time = datetime.strptime(rule["ModificationTime"], time_format)
    modification_time = modification_time.replace(tzinfo=None)
    assert modification_time <= now


@mock_ec2
@mock_route53resolver
def test_route53resolver_bad_create_resolver_rule():
    """Test error scenarios for create_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    random_num = get_random_hex(10)

    # Create a good endpoint and rule that we can use to test.
    created_endpoint = create_test_endpoint(client, ec2_client)
    endpoint_id = created_endpoint["Id"]
    created_rule = create_test_rule(client)
    creator_request_id = created_rule["CreatorRequestId"]

    # Attempt to create another rule with the same creator request id.
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=creator_request_id,
            Name="B" + random_num,
            RuleType="FORWARD",
            DomainName=f"{random_num}.test",
            TargetIps=[{"Ip": "1.2.3.4", "Port": 5}],
            ResolverEndpointId=endpoint_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceExistsException"
    assert (
        f"Resolver rule with creator request ID '{creator_request_id}' already exists"
    ) in err["Message"]

    # Attempt to create a rule with a IPv6 address.
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=get_random_hex(10),
            Name="B" + random_num,
            RuleType="FORWARD",
            DomainName=f"{random_num}.test",
            TargetIps=[{"Ip": "201:db8:1234::", "Port": 5}],
            ResolverEndpointId=endpoint_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "Only IPv4 addresses may be used: '201:db8:1234::'" in err["Message"]

    # Attempt to create a rule with an invalid IPv4 address.
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=get_random_hex(10),
            Name="B" + random_num,
            RuleType="FORWARD",
            DomainName=f"{random_num}.test",
            TargetIps=[{"Ip": "20.1.2:", "Port": 5}],
            ResolverEndpointId=endpoint_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "Invalid IP address: '20.1.2:'" in err["Message"]

    # Attempt to create a rule with a non-existent resolver endpoint id.
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=get_random_hex(10),
            Name="B" + random_num,
            RuleType="FORWARD",
            DomainName=f"{random_num}.test",
            TargetIps=[{"Ip": "1.2.3.4", "Port": 5}],
            ResolverEndpointId="fooey",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Resolver endpoint with ID 'fooey' does not exist" in err["Message"]

    # Create a rule with a resolver endpoint id and a rule type of SYSTEM.
    with pytest.raises(ClientError) as exc:
        client.create_resolver_rule(
            CreatorRequestId=get_random_hex(10),
            Name="B" + random_num,
            RuleType="SYSTEM",
            DomainName=f"{random_num}.test",
            TargetIps=[{"Ip": "1.2.3.4", "Port": 5}],
            ResolverEndpointId=endpoint_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert (
        "Cannot specify resolver endpoint ID and target IP for SYSTEM type "
        "resolver rule"
    ) in err["Message"]

    # Too many rules.
    for _ in range(1000):
        create_test_rule(client)
    with pytest.raises(ClientError) as exc:
        create_test_rule(client)
    err = exc.value.response["Error"]
    assert err["Code"] == "LimitExceededException"
    assert f"Account '{ACCOUNT_ID}' has exceeded 'max-rules" in err["Message"]
