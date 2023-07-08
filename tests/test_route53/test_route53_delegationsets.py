import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_route53


@mock_route53
def test_list_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    resp = client.list_reusable_delegation_sets()

    assert resp["DelegationSets"] == []
    assert resp["IsTruncated"] is False


@mock_route53
def test_create_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    resp = client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")

    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    assert "location" in headers

    assert "Id" in resp["DelegationSet"]
    assert resp["DelegationSet"]["CallerReference"] == "r3f3r3nc3"
    assert len(resp["DelegationSet"]["NameServers"]) == 4


@mock_route53
def test_create_reusable_delegation_set_from_hosted_zone():
    client = boto3.client("route53", region_name="us-east-1")
    response = client.create_hosted_zone(
        Name="testdns.aws.com.", CallerReference=str(hash("foo"))
    )
    hosted_zone_id = response["HostedZone"]["Id"]
    hosted_zone_name_servers = set(response["DelegationSet"]["NameServers"])

    resp = client.create_reusable_delegation_set(
        CallerReference="r3f3r3nc3", HostedZoneId=hosted_zone_id
    )

    assert set(resp["DelegationSet"]["NameServers"]) == hosted_zone_name_servers


@mock_route53
def test_create_reusable_delegation_set_from_hosted_zone_with_delegationsetid():
    client = boto3.client("route53", region_name="us-east-1")
    response = client.create_hosted_zone(
        Name="testdns.aws.com.",
        CallerReference=str(hash("foo")),
        DelegationSetId="customdelegationsetid",
    )

    assert response["DelegationSet"]["Id"] == "customdelegationsetid"

    hosted_zone_id = response["HostedZone"]["Id"]
    hosted_zone_name_servers = set(response["DelegationSet"]["NameServers"])

    resp = client.create_reusable_delegation_set(
        CallerReference="r3f3r3nc3", HostedZoneId=hosted_zone_id
    )

    assert resp["DelegationSet"]["Id"] != "customdelegationsetid"
    assert set(resp["DelegationSet"]["NameServers"]) == hosted_zone_name_servers


@mock_route53
def test_get_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    ds_id = client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")[
        "DelegationSet"
    ]["Id"]

    resp = client.get_reusable_delegation_set(Id=ds_id)

    assert "DelegationSet" in resp

    assert resp["DelegationSet"]["Id"] == ds_id
    assert resp["DelegationSet"]["CallerReference"] == "r3f3r3nc3"
    assert len(resp["DelegationSet"]["NameServers"]) == 4


@mock_route53
def test_get_reusable_delegation_set_unknown():
    client = boto3.client("route53", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_reusable_delegation_set(Id="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchDelegationSet"
    assert err["Message"] == "unknown"


@mock_route53
def test_list_reusable_delegation_sets():
    client = boto3.client("route53", region_name="us-east-1")
    client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")
    client.create_reusable_delegation_set(CallerReference="r3f3r3nc4")

    resp = client.list_reusable_delegation_sets()
    assert len(resp["DelegationSets"]) == 2
    assert resp["IsTruncated"] is False


@mock_route53
def test_delete_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    ds_id = client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")[
        "DelegationSet"
    ]["Id"]

    client.delete_reusable_delegation_set(Id=ds_id)

    assert len(client.list_reusable_delegation_sets()["DelegationSets"]) == 0
