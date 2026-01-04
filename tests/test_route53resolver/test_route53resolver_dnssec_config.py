"""Unit tests for Route53Resolver DNSSEC APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

TEST_REGION = "us-east-1"


@mock_aws
def test_update_resolver_dnssec_config_lifecycle():
    client = boto3.client("route53resolver", region_name=TEST_REGION)

    vpc_id = "vpc-lifecycle-test"

    create_resp = client.update_resolver_dnssec_config(
        ResourceId=vpc_id, Validation="ENABLE"
    )

    config = create_resp["ResolverDNSSECConfig"]
    assert config["ResourceId"] == vpc_id
    assert config["ValidationStatus"] == "ENABLED"
    assert config["OwnerId"]
    assert config["Id"].startswith("rdsc-")

    get_resp = client.get_resolver_dnssec_config(ResourceId=vpc_id)
    get_config = get_resp["ResolverDNSSECConfig"]

    assert get_config["ResourceId"] == vpc_id
    assert get_config["ValidationStatus"] == "ENABLED"

    update_resp = client.update_resolver_dnssec_config(
        ResourceId=vpc_id, Validation="DISABLE"
    )

    updated_config = update_resp["ResolverDNSSECConfig"]
    assert updated_config["ValidationStatus"] == "DISABLED"

    final_resp = client.get_resolver_dnssec_config(ResourceId=vpc_id)
    assert final_resp["ResolverDNSSECConfig"]["ValidationStatus"] == "DISABLED"


@mock_aws
def test_get_nonexistent_resolver_dnssec_config():
    """Test retrieving a configuration that does not exist."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)
    vpc_id = "vpc-nonexistent"

    with pytest.raises(ClientError) as exc:
        client.get_resolver_dnssec_config(ResourceId=vpc_id)

    error = exc.value.response["Error"]
    assert error["Code"] == "ResourceNotFoundException"
    assert (
        f"Resolver DNSSEC configuration for '{vpc_id}' does not exist"
        in error["Message"]
    )


@mock_aws
def test_list_resolver_dnssec_configs_pagination():
    """Test listing configurations with pagination (NextToken)."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)

    for i in range(4):
        client.update_resolver_dnssec_config(
            ResourceId=f"vpc-page-{i}", Validation="ENABLE"
        )

    page1 = client.list_resolver_dnssec_configs(MaxResults=2)
    assert len(page1["ResolverDnssecConfigs"]) == 2
    assert "NextToken" in page1

    page2 = client.list_resolver_dnssec_configs(
        MaxResults=2, NextToken=page1["NextToken"]
    )
    assert len(page2["ResolverDnssecConfigs"]) == 2
    assert "NextToken" not in page2

    ids_1 = [c["ResourceId"] for c in page1["ResolverDnssecConfigs"]]
    ids_2 = [c["ResourceId"] for c in page2["ResolverDnssecConfigs"]]
    all_ids = sorted(ids_1 + ids_2)

    expected = ["vpc-page-0", "vpc-page-1", "vpc-page-2", "vpc-page-3"]
    assert all_ids == expected


@mock_aws
def test_list_resolver_dnssec_configs_filtering():
    """Test listing configurations with Filters."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)

    client.update_resolver_dnssec_config(ResourceId="vpc-A", Validation="ENABLE")
    client.update_resolver_dnssec_config(ResourceId="vpc-B", Validation="DISABLE")
    client.update_resolver_dnssec_config(ResourceId="vpc-C", Validation="ENABLE")

    response = client.list_resolver_dnssec_configs(
        Filters=[{"Name": "ResourceId", "Values": ["vpc-B"]}]
    )

    items = response["ResolverDnssecConfigs"]
    assert len(items) == 1
    assert items[0]["ResourceId"] == "vpc-B"
    assert items[0]["ValidationStatus"] == "DISABLED"


@mock_aws
def test_list_resolver_dnssec_configs_empty():
    """Test listing when no configurations exist."""
    client = boto3.client("route53resolver", region_name=TEST_REGION)

    response = client.list_resolver_dnssec_configs()
    assert len(response["ResolverDnssecConfigs"]) == 0
    assert "NextToken" not in response
