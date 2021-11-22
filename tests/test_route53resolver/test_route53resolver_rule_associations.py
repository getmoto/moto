"""Unit tests for route53resolver rule association-related APIs."""
import boto3
from botocore.exceptions import ClientError

import pytest

from moto import mock_route53resolver
from moto.core.utils import get_random_hex
from moto.ec2 import mock_ec2

from .test_route53resolver_endpoint import TEST_REGION, create_vpc
from .test_route53resolver_rule import create_test_rule


def create_test_rule_association(
    client, ec2_client, resolver_rule_id=None, name=None, vpc_id=None
):
    """Create a Resolver Rule Association for testing purposes."""
    if not resolver_rule_id:
        resolver_rule_id = create_test_rule(client)["Id"]
    name = name if name else "R" + get_random_hex(10)
    if not vpc_id:
        vpc_id = create_vpc(ec2_client)
    return client.associate_resolver_rule(
        ResolverRuleId=resolver_rule_id, Name=name, VPCId=vpc_id
    )["ResolverRuleAssociation"]


@mock_route53resolver
def test_route53resolver_invalid_associate_resolver_rule_args():
    """Test invalid arguments to the associate_resolver_rule API."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    random_num = get_random_hex(10)

    # Verify ValidationException error messages are accumulated properly:
    #  - resolver rule ID that exceeds the allowed length of 64.
    #  - name that exceeds the allowed length of 64.
    #  - vpc_id that exceeds the allowed length of 64.
    long_id = random_num * 7
    long_name = random_num * 6 + "abcde"
    long_vpc_id = random_num * 6 + "fghij"
    with pytest.raises(ClientError) as exc:
        client.associate_resolver_rule(
            ResolverRuleId=long_id, Name=long_name, VPCId=long_vpc_id,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "3 validation errors detected" in err["Message"]
    assert (
        f"Value '{long_id}' at 'resolverRuleId' failed to satisfy "
        f"constraint: Member must have length less than or equal to 64"
    ) in err["Message"]
    assert (
        f"Value '{long_name}' at 'name' failed to satisfy constraint: "
        f"Member must have length less than or equal to 64"
    ) in err["Message"]
    assert (
        f"Value '{long_vpc_id}' at 'vPCId' failed to satisfy "
        f"constraint: Member must have length less than or equal to 64"
    ) in err["Message"]


@mock_ec2
@mock_route53resolver
def test_route53resolver_associate_resolver_rule():
    """Test good associate_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    resolver_rule_id = create_test_rule(client)["Id"]
    name = "X" + get_random_hex(10)
    vpc_id = create_vpc(ec2_client)
    rule_association = client.associate_resolver_rule(
        ResolverRuleId=resolver_rule_id, Name=name, VPCId=vpc_id,
    )["ResolverRuleAssociation"]
    assert rule_association["Id"].startswith("rslvr-rrassoc-")
    assert rule_association["ResolverRuleId"] == resolver_rule_id
    assert rule_association["Name"] == name
    assert rule_association["VPCId"] == vpc_id
    assert rule_association["Status"] == "COMPLETE"
    assert "StatusMessage" in rule_association


@mock_ec2
@mock_route53resolver
def test_route53resolver_other_associate_resolver_rule_errors():
    """Test good associate_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Resolver referenced by resolver_rule_id doesn't exist.
    with pytest.raises(ClientError) as exc:
        create_test_rule_association(client, ec2_client, resolver_rule_id="foo")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert "Resolver rule with ID 'foo' does not exist" in err["Message"]

    # Invalid vpc_id
    with pytest.raises(ClientError) as exc:
        create_test_rule_association(client, ec2_client, vpc_id="foo")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert "The vpc ID 'foo' does not exist" in err["Message"]

    # Same resolver_rule_id and vpc_id pair for an association.
    resolver_rule_id = create_test_rule(client)["Id"]
    vpc_id = create_vpc(ec2_client)
    create_test_rule_association(
        client, ec2_client, resolver_rule_id=resolver_rule_id, vpc_id=vpc_id
    )
    with pytest.raises(ClientError) as exc:
        create_test_rule_association(
            client, ec2_client, resolver_rule_id=resolver_rule_id, vpc_id=vpc_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert (
        f"Cannot associate rules with same domain name with same VPC. "
        f"Conflict with resolver rule '{resolver_rule_id}'"
    ) in err["Message"]

    # Not testing "Too many rule associations" as it takes too long to create
    # 2000 VPCs and rule associations.


@mock_ec2
@mock_route53resolver
def test_route53resolver_disassociate_resolver_rule():
    """Test good disassociate_resolver_rule API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    created_association = create_test_rule_association(client, ec2_client)

    # Disassociate the resolver rule and verify the response.
    response = client.disassociate_resolver_rule(
        ResolverRuleId=created_association["ResolverRuleId"],
        VPCId=created_association["VPCId"],
    )
    association = response["ResolverRuleAssociation"]
    assert association["Id"] == created_association["Id"]
    assert association["ResolverRuleId"] == created_association["ResolverRuleId"]
    assert association["Name"] == created_association["Name"]
    assert association["VPCId"] == created_association["VPCId"]
    assert association["Status"] == "DELETING"
    assert "Deleting" in association["StatusMessage"]


@mock_ec2
@mock_route53resolver
def test_route53resolver_bad_disassociate_resolver_rule():
    """Test disassociate_resolver_rule API calls with a bad ID."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)
    random_num = get_random_hex(10)

    # Use a resolver rule id and vpc id that is too long.
    long_id = "0123456789" * 6 + "xxxxx"
    long_vpc_id = random_num * 6 + "12345"
    with pytest.raises(ClientError) as exc:
        client.disassociate_resolver_rule(ResolverRuleId=long_id, VPCId=long_vpc_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "2 validation errors detected" in err["Message"]
    assert (
        f"Value '{long_id}' at 'resolverRuleId' failed to satisfy "
        f"constraint: Member must have length less than or equal to 64"
    ) in err["Message"]
    assert (
        f"Value '{long_vpc_id}' at 'vPCId' failed to satisfy "
        f"constraint: Member must have length less than or equal to 64"
    ) in err["Message"]

    # Create a test association.
    test_association = create_test_rule_association(client, ec2_client)
    test_rule_id = test_association["ResolverRuleId"]
    test_vpc_id = test_association["VPCId"]

    # Disassociate from a non-existent resolver rule id.
    with pytest.raises(ClientError) as exc:
        client.disassociate_resolver_rule(ResolverRuleId=random_num, VPCId=test_vpc_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"Resolver rule with ID '{random_num}' does not exist" in err["Message"]

    # Disassociate using a non-existent vpc id.
    with pytest.raises(ClientError) as exc:
        client.disassociate_resolver_rule(ResolverRuleId=test_rule_id, VPCId=random_num)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        f"Resolver Rule Association between Resolver Rule "
        f"'{test_rule_id}' and VPC '{random_num}' does not exist"
    ) in err["Message"]

    # Disassociate successfully, then test that it's not possible to
    # disassociate again.
    client.disassociate_resolver_rule(ResolverRuleId=test_rule_id, VPCId=test_vpc_id)
    with pytest.raises(ClientError) as exc:
        client.disassociate_resolver_rule(
            ResolverRuleId=test_rule_id, VPCId=test_vpc_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        f"Resolver Rule Association between Resolver Rule "
        f"'{test_rule_id}' and VPC '{test_vpc_id}' does not exist"
    ) in err["Message"]


@mock_ec2
@mock_route53resolver
def test_route53resolver_get_resolver_rule_association():
    """Test good get_resolver_rule_association API calls."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    ec2_client = boto3.client("ec2", region_name=TEST_REGION)

    # Create a good association for testing purposes.
    created_association = create_test_rule_association(client, ec2_client)

    # Now get the resolver rule association and verify the response.
    response = client.get_resolver_rule_association(
        ResolverRuleAssociationId=created_association["Id"]
    )
    association = response["ResolverRuleAssociation"]
    assert association["Id"] == created_association["Id"]
    assert association["ResolverRuleId"] == created_association["ResolverRuleId"]
    assert association["Name"] == created_association["Name"]
    assert association["VPCId"] == created_association["VPCId"]
    assert association["Status"] == created_association["Status"]
    assert association["StatusMessage"] == created_association["StatusMessage"]


@mock_route53resolver
def test_route53resolver_bad_get_resolver_rule_association():
    """Test get_resolver_rule_association API calls with a bad ID."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    random_num = get_random_hex(10)

    # Use a resolver rule association id that is too long.
    long_id = "0123456789" * 6 + "xxxxx"
    with pytest.raises(ClientError) as exc:
        client.get_resolver_rule_association(ResolverRuleAssociationId=long_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert "1 validation error detected" in err["Message"]
    assert (
        f"Value '{long_id}' at 'resolverRuleAssociationId' failed to satisfy "
        f"constraint: Member must have length less than or equal to 64"
    ) in err["Message"]

    # Get a non-existent resolver rule association.
    with pytest.raises(ClientError) as exc:
        client.get_resolver_rule_association(ResolverRuleAssociationId=random_num)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert f"ResolverRuleAssociation '{random_num}' does not Exist" in err["Message"]
