from datetime import datetime, timezone

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.moto_api._internal import mock_random

from .test_route53resolver_endpoint import TEST_REGION, create_test_endpoint, create_vpc


def create_test_rule(client, name=None, tags=None):
    """Create an rule that can be used for testing purposes.

    Can't be used for unit tests that need to know/test the arguments.
    """
    if not tags:
        tags = []
    random_num = mock_random.get_random_hex(10)

    resolver_rule = client.create_resolver_rule(
        CreatorRequestId=random_num,
        Name=name if name else "X" + random_num,
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


@mock_aws
def test_route53resolver_invalid_create_rule_args():
    """Test invalid arguments to the create_resolver_rule API."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(10)

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


@mock_aws
def test_route53resolver_create_resolver_rule():  # pylint: disable=too-many-locals
    """Test good create_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(10)

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
    assert rule["DomainName"] == domain_name + "."
    assert rule["Status"] == "COMPLETE"
    assert "Successfully created Resolver Rule" in rule["StatusMessage"]
    assert rule["RuleType"] == "FORWARD"
    assert rule["Name"] == name
    assert len(rule["TargetIps"]) == 1
    assert rule["TargetIps"][0]["Ip"] == target_ips[0]["Ip"]
    assert rule["TargetIps"][0]["Port"] == target_ips[0]["Port"]
    assert rule["ResolverEndpointId"] == endpoint_id
    assert rule["OwnerId"] == ACCOUNT_ID
    assert rule["ShareStatus"] == "NOT_SHARED"

    time_format = "%Y-%m-%dT%H:%M:%S.%f+00:00"
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    creation_time = datetime.strptime(rule["CreationTime"], time_format)
    creation_time = creation_time.replace(tzinfo=None)
    assert creation_time <= now

    modification_time = datetime.strptime(rule["ModificationTime"], time_format)
    modification_time = modification_time.replace(tzinfo=None)
    assert modification_time <= now


@mock_aws
def test_route53resolver_bad_create_resolver_rule():
    """Test error scenarios for create_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(10)

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
            CreatorRequestId=mock_random.get_random_hex(10),
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
            CreatorRequestId=mock_random.get_random_hex(10),
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
            CreatorRequestId=mock_random.get_random_hex(10),
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
            CreatorRequestId=mock_random.get_random_hex(10),
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


@mock_aws
def test_route53resolver_delete_resolver_rule():
    """Test good delete_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    created_rule = create_test_rule(client)

    # Now delete the resolver rule and verify the response.
    response = client.delete_resolver_rule(ResolverRuleId=created_rule["Id"])
    rule = response["ResolverRule"]
    assert rule["Id"] == created_rule["Id"]
    assert rule["CreatorRequestId"] == created_rule["CreatorRequestId"]
    assert rule["Arn"] == created_rule["Arn"]
    assert rule["DomainName"] == created_rule["DomainName"]
    assert rule["Status"] == "DELETING"
    assert "Deleting" in rule["StatusMessage"]
    assert rule["RuleType"] == created_rule["RuleType"]
    assert rule["Name"] == created_rule["Name"]
    assert rule["TargetIps"] == created_rule["TargetIps"]
    assert rule["OwnerId"] == created_rule["OwnerId"]
    assert rule["ShareStatus"] == created_rule["ShareStatus"]
    assert rule["CreationTime"] == created_rule["CreationTime"]


@mock_aws
def test_route53resolver_bad_delete_resolver_rule():
    """Test delete_resolver_rule API calls with a bad ID."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(10)

    # Use a resolver rule id that is too long.
    long_id = "0123456789" * 6 + "xxxxx"
    with pytest.raises(ClientError) as exc:
        client.delete_resolver_rule(ResolverRuleId=long_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{long_id}' at 'resolverRuleId' failed to satisfy "
        f"constraint: Member must have length less than or equal to 64"
    ) in err["Message"]

    # Delete a non-existent resolver rule.
    with pytest.raises(ClientError) as exc:
        client.delete_resolver_rule(ResolverRuleId=random_num)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Resolver rule with ID '{random_num}' does not exist" in err["Message"]

    # Verify a rule can't be deleted if VPCs are associated with it.
    test_rule = create_test_rule(client)
    vpc_id = create_vpc(ec2_client)
    client.associate_resolver_rule(ResolverRuleId=test_rule["Id"], VPCId=vpc_id)
    with pytest.raises(ClientError) as exc:
        client.delete_resolver_rule(ResolverRuleId=test_rule["Id"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceInUseException"
    assert (
        "Please disassociate this resolver rule from VPC first before deleting"
    ) in err["Message"]


@mock_aws
def test_route53resolver_get_resolver_rule():
    """Test good get_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    created_rule = create_test_rule(client)

    # Now get the resolver rule and verify the response.
    response = client.get_resolver_rule(ResolverRuleId=created_rule["Id"])
    rule = response["ResolverRule"]
    assert rule["Id"] == created_rule["Id"]
    assert rule["CreatorRequestId"] == created_rule["CreatorRequestId"]
    assert rule["Arn"] == created_rule["Arn"]
    assert rule["DomainName"] == created_rule["DomainName"]
    assert rule["Status"] == created_rule["Status"]
    assert rule["StatusMessage"] == created_rule["StatusMessage"]
    assert rule["RuleType"] == created_rule["RuleType"]
    assert rule["Name"] == created_rule["Name"]
    assert rule["TargetIps"] == created_rule["TargetIps"]
    assert rule["OwnerId"] == created_rule["OwnerId"]
    assert rule["ShareStatus"] == created_rule["ShareStatus"]
    assert rule["CreationTime"] == created_rule["CreationTime"]
    assert rule["ModificationTime"] == created_rule["ModificationTime"]


@mock_aws
def test_route53resolver_bad_get_resolver_rule():
    """Test get_resolver_rule API calls with a bad ID."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(10)

    # Use a resolver rule id that is too long.
    long_id = "0123456789" * 6 + "xxxxx"
    with pytest.raises(ClientError) as exc:
        client.get_resolver_rule(ResolverRuleId=long_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{long_id}' at 'resolverRuleId' failed to satisfy "
        f"constraint: Member must have length less than or equal to 64"
    ) in err["Message"]

    # Delete a non-existent resolver rule.
    with pytest.raises(ClientError) as exc:
        client.get_resolver_rule(ResolverRuleId=random_num)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Resolver rule with ID '{random_num}' does not exist" in err["Message"]


@mock_aws
def test_route53resolver_list_resolver_rules():
    """Test good list_resolver_rules API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(10)

    # List rules when there are none.
    response = client.list_resolver_rules()
    assert len(response["ResolverRules"]) == 0
    assert response["MaxResults"] == 10
    assert "NextToken" not in response

    # Create 4 rules, verify all 4 are listed when no filters, max_results.
    for idx in range(4):
        create_test_rule(client, name=f"A{idx}-{random_num}")
    response = client.list_resolver_rules()
    rules = response["ResolverRules"]
    assert len(rules) == 4
    assert response["MaxResults"] == 10
    for idx in range(4):
        assert rules[idx]["Name"].startswith(f"A{idx}")

    # Set max_results to return 1 rule, use next_token to get remaining 3.
    response = client.list_resolver_rules(MaxResults=1)
    rules = response["ResolverRules"]
    assert len(rules) == 1
    assert response["MaxResults"] == 1
    assert "NextToken" in response
    assert rules[0]["Name"].startswith("A0")

    response = client.list_resolver_rules(NextToken=response["NextToken"])
    rules = response["ResolverRules"]
    assert len(rules) == 3
    assert response["MaxResults"] == 10
    assert "NextToken" not in response
    for idx, rule in enumerate(rules):
        assert rule["Name"].startswith(f"A{idx + 1}")


@mock_aws
def test_route53resolver_list_resolver_rules_filters():
    """Test good list_resolver_rules API calls that use filters."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    random_num = mock_random.get_random_hex(10)

    # Create some endpoints and rules for testing purposes.
    endpoint1 = create_test_endpoint(client, ec2_client)["Id"]
    endpoint2 = create_test_endpoint(client, ec2_client)["Id"]

    rules = []
    for idx in range(1, 5):
        response = client.create_resolver_rule(
            CreatorRequestId=f"F{idx}-{random_num}",
            Name=f"F{idx}-{random_num}",
            RuleType="FORWARD" if idx % 2 else "RECURSIVE",
            DomainName=f"test{idx}.test",
            TargetIps=[{"Ip": f"10.0.1.{idx}", "Port": 50 + idx}],
            ResolverEndpointId=endpoint1 if idx % 2 else endpoint2,
        )
        rules.append(response["ResolverRule"])

    # Try all the valid filter names, including some of the old style names.
    response = client.list_resolver_rules(
        Filters=[{"Name": "CreatorRequestId", "Values": [f"F3-{random_num}"]}]
    )
    assert len(response["ResolverRules"]) == 1
    assert response["ResolverRules"][0]["CreatorRequestId"] == f"F3-{random_num}"

    response = client.list_resolver_rules(
        Filters=[
            {
                "Name": "CREATOR_REQUEST_ID",
                "Values": [f"F2-{random_num}", f"F4-{random_num}"],
            }
        ]
    )
    assert len(response["ResolverRules"]) == 2
    assert response["ResolverRules"][0]["CreatorRequestId"] == f"F2-{random_num}"
    assert response["ResolverRules"][1]["CreatorRequestId"] == f"F4-{random_num}"

    response = client.list_resolver_rules(
        Filters=[{"Name": "Type", "Values": ["FORWARD"]}]
    )
    assert len(response["ResolverRules"]) == 2
    assert response["ResolverRules"][0]["CreatorRequestId"] == f"F1-{random_num}"
    assert response["ResolverRules"][1]["CreatorRequestId"] == f"F3-{random_num}"

    response = client.list_resolver_rules(
        Filters=[{"Name": "Name", "Values": [f"F1-{random_num}"]}]
    )
    assert len(response["ResolverRules"]) == 1
    assert response["ResolverRules"][0]["Name"] == f"F1-{random_num}"

    response = client.list_resolver_rules(
        Filters=[
            {"Name": "RESOLVER_ENDPOINT_ID", "Values": [endpoint1, endpoint2]},
            {"Name": "TYPE", "Values": ["FORWARD"]},
            {"Name": "NAME", "Values": [f"F3-{random_num}"]},
        ]
    )
    assert len(response["ResolverRules"]) == 1
    assert response["ResolverRules"][0]["Name"] == f"F3-{random_num}"

    response = client.list_resolver_rules(
        Filters=[{"Name": "DomainName", "Values": ["test4.test."]}]
    )
    assert len(response["ResolverRules"]) == 1
    assert response["ResolverRules"][0]["Name"] == f"F4-{random_num}"

    response = client.list_resolver_rules(
        Filters=[{"Name": "Status", "Values": ["COMPLETE"]}]
    )
    assert len(response["ResolverRules"]) == 4
    response = client.list_resolver_rules(
        Filters=[{"Name": "Status", "Values": ["FAILED"]}]
    )
    assert len(response["ResolverRules"]) == 0


@mock_aws
def test_route53resolver_bad_list_resolver_rules_filters():
    """Test bad list_resolver_rules API calls that use filters."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)

    # botocore barfs on an empty "Values":
    # TypeError: list_resolver_rules() only accepts keyword arguments.
    # client.list_resolver_rules([{"Name": "Direction", "Values": []}])
    # client.list_resolver_rules([{"Values": []}])

    with pytest.raises(ClientError) as exc:
        client.list_resolver_rules(Filters=[{"Name": "foo", "Values": ["bar"]}])
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "The filter 'foo' is invalid" in err["Message"]


@mock_aws
def test_route53resolver_bad_list_resolver_rules():
    """Test bad list_resolver_rules API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)

    # Bad max_results.
    random_num = mock_random.get_random_hex(10)
    create_test_rule(client, name=f"A-{random_num}")
    with pytest.raises(ClientError) as exc:
        client.list_resolver_rules(MaxResults=250)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        "Value '250' at 'maxResults' failed to satisfy constraint: Member "
        "must have length less than or equal to 100"
    ) in err["Message"]
