import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_route53


@mock_route53
def test_list_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    resp = client.list_reusable_delegation_sets()

    resp.should.have.key("DelegationSets").equals([])
    resp.should.have.key("IsTruncated").equals(False)


@mock_route53
def test_create_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    resp = client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")

    headers = resp["ResponseMetadata"]["HTTPHeaders"]
    headers.should.have.key("location")

    resp.should.have.key("DelegationSet")

    resp["DelegationSet"].should.have.key("Id")
    resp["DelegationSet"].should.have.key("CallerReference").equals("r3f3r3nc3")
    resp["DelegationSet"].should.have.key("NameServers").length_of(4)


@mock_route53
def test_create_reusable_delegation_set_from_hosted_zone():
    client = boto3.client("route53", region_name="us-east-1")
    response = client.create_hosted_zone(
        Name="testdns.aws.com.", CallerReference=str(hash("foo"))
    )
    hosted_zone_id = response["HostedZone"]["Id"]
    print(response)
    hosted_zone_name_servers = set(response["DelegationSet"]["NameServers"])

    resp = client.create_reusable_delegation_set(
        CallerReference="r3f3r3nc3", HostedZoneId=hosted_zone_id
    )

    set(resp["DelegationSet"]["NameServers"]).should.equal(hosted_zone_name_servers)


@mock_route53
def test_create_reusable_delegation_set_from_hosted_zone_with_delegationsetid():
    client = boto3.client("route53", region_name="us-east-1")
    response = client.create_hosted_zone(
        Name="testdns.aws.com.",
        CallerReference=str(hash("foo")),
        DelegationSetId="customdelegationsetid",
    )

    response.should.have.key("DelegationSet")
    response["DelegationSet"].should.have.key("Id").equals("customdelegationsetid")
    response["DelegationSet"].should.have.key("NameServers")

    hosted_zone_id = response["HostedZone"]["Id"]
    hosted_zone_name_servers = set(response["DelegationSet"]["NameServers"])

    resp = client.create_reusable_delegation_set(
        CallerReference="r3f3r3nc3", HostedZoneId=hosted_zone_id
    )

    resp["DelegationSet"].should.have.key("Id").shouldnt.equal("customdelegationsetid")
    set(resp["DelegationSet"]["NameServers"]).should.equal(hosted_zone_name_servers)


@mock_route53
def test_get_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    ds_id = client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")[
        "DelegationSet"
    ]["Id"]

    resp = client.get_reusable_delegation_set(Id=ds_id)

    resp.should.have.key("DelegationSet")

    resp["DelegationSet"].should.have.key("Id").equals(ds_id)
    resp["DelegationSet"].should.have.key("CallerReference").equals("r3f3r3nc3")
    resp["DelegationSet"].should.have.key("NameServers").length_of(4)


@mock_route53
def test_get_reusable_delegation_set_unknown():
    client = boto3.client("route53", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_reusable_delegation_set(Id="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NoSuchDelegationSet")
    err["Message"].should.equal("unknown")


@mock_route53
def test_list_reusable_delegation_sets():
    client = boto3.client("route53", region_name="us-east-1")
    client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")
    client.create_reusable_delegation_set(CallerReference="r3f3r3nc4")

    resp = client.list_reusable_delegation_sets()
    resp.should.have.key("DelegationSets").length_of(2)
    resp.should.have.key("IsTruncated").equals(False)


@mock_route53
def test_delete_reusable_delegation_set():
    client = boto3.client("route53", region_name="us-east-1")
    ds_id = client.create_reusable_delegation_set(CallerReference="r3f3r3nc3")[
        "DelegationSet"
    ]["Id"]

    client.delete_reusable_delegation_set(Id=ds_id)

    client.list_reusable_delegation_sets()["DelegationSets"].should.have.length_of(0)
