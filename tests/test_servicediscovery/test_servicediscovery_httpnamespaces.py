import re

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_http_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(Name="mynamespace")

    resp = client.list_namespaces()
    assert len(resp["Namespaces"]) == 1

    namespace = resp["Namespaces"][0]
    assert re.match("ns-[a-z0-9]{16}", namespace["Id"])
    assert re.match(
        f"arn:aws:servicediscovery:eu-west-1:{ACCOUNT_ID}:namespace/{namespace['Id']}",
        namespace["Arn"],
    )
    assert namespace["Name"] == "mynamespace"
    assert namespace["Type"] == "HTTP"
    assert "CreateDate" in namespace

    assert "Properties" in namespace
    props = namespace["Properties"]
    assert props["DnsProperties"] == {"SOA": {}}
    assert props["HttpProperties"] == {"HttpName": "mynamespace"}


@mock_aws
def test_get_http_namespace_minimal():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(Name="mynamespace")

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    assert "Namespace" in resp

    namespace = resp["Namespace"]
    assert re.match(ns_id, namespace["Id"])
    assert re.match(
        f"arn:aws:servicediscovery:eu-west-1:{ACCOUNT_ID}:namespace/{namespace['Id']}",
        namespace["Arn"],
    )
    assert namespace["Name"] == "mynamespace"
    assert namespace["Type"] == "HTTP"
    assert "CreateDate" in namespace
    assert "CreatorRequestId" in namespace

    assert "Properties" in namespace
    props = namespace["Properties"]
    assert props["DnsProperties"] == {"SOA": {}}
    assert props["HttpProperties"] == {"HttpName": "mynamespace"}

    assert "Description" not in namespace


@mock_aws
def test_get_http_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(
        Name="mynamespace", CreatorRequestId="crid", Description="mu fancy namespace"
    )

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    assert "Namespace" in resp

    namespace = resp["Namespace"]
    assert re.match(ns_id, namespace["Id"])
    assert re.match(
        f"arn:aws:servicediscovery:eu-west-1:{ACCOUNT_ID}:namespace/{namespace['Id']}",
        namespace["Arn"],
    )
    assert namespace["Name"] == "mynamespace"
    assert namespace["Type"] == "HTTP"
    assert "CreateDate" in namespace
    assert namespace["CreatorRequestId"] == "crid"
    assert namespace["Description"] == "mu fancy namespace"

    assert "Properties" in namespace
    props = namespace["Properties"]
    assert props["DnsProperties"] == {"SOA": {}}
    assert props["HttpProperties"] == {"HttpName": "mynamespace"}


@mock_aws
def test_delete_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(Name="mynamespace")
    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.delete_namespace(Id=ns_id)
    assert "OperationId" in resp

    # Calling delete again while this is in progress results in an error:
    #    Another operation of type DeleteNamespace and id
    #    dlmpkcn33aovnztwdpsdplgtheuhgcap-k6x64euq is in progress
    # list_operations is empty after successfull deletion - old operations
    #    from this namespace should be deleted
    # list_namespaces is also empty (obvs)

    assert client.list_namespaces()["Namespaces"] == []
    assert client.list_operations()["Operations"] == []


@mock_aws
def test_delete_unknown_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.delete_namespace(Id="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NamespaceNotFound"
    assert err["Message"] == "unknown"


@mock_aws
def test_get_unknown_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.get_namespace(Id="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NamespaceNotFound"
    assert err["Message"] == "unknown"


@mock_aws
def test_create_private_dns_namespace_minimal():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_private_dns_namespace(Name="dns_ns", Vpc="vpc_id")

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    assert "Namespace" in resp

    namespace = resp["Namespace"]
    assert re.match(ns_id, namespace["Id"])
    assert namespace["Name"] == "dns_ns"
    assert namespace["Type"] == "DNS_PRIVATE"

    assert "Properties" in namespace
    props = namespace["Properties"]
    assert "DnsProperties" in props
    assert "HostedZoneId" in props["DnsProperties"]
    assert "SOA" not in props["DnsProperties"]


@mock_aws
def test_create_private_dns_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_private_dns_namespace(
        Name="dns_ns",
        Vpc="vpc_id",
        Description="my private dns",
        Properties={"DnsProperties": {"SOA": {"TTL": 123}}},
    )

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    assert "Namespace" in resp

    namespace = resp["Namespace"]
    assert re.match(ns_id, namespace["Id"])
    assert namespace["Name"] == "dns_ns"
    assert namespace["Type"] == "DNS_PRIVATE"
    assert namespace["Description"] == "my private dns"

    assert "Properties" in namespace
    props = namespace["Properties"]
    assert "DnsProperties" in props
    assert "HostedZoneId" in props["DnsProperties"]
    assert props["DnsProperties"]["SOA"] == {"TTL": 123}


@mock_aws
def test_update_private_dns_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_private_dns_namespace(
        Name="dns_ns",
        Vpc="vpc_id",
        Description="my private dns",
        Properties={"DnsProperties": {"SOA": {"TTL": 123}}},
    )

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    client.update_private_dns_namespace(
        Id=ns_id,
        Namespace={
            "Description": "updated dns",
            "Properties": {"DnsProperties": {"SOA": {"TTL": 654}}},
        },
    )

    namespace = client.get_namespace(Id=ns_id)["Namespace"]
    assert namespace["Description"] == "updated dns"

    props = namespace["Properties"]
    assert props["DnsProperties"]["SOA"] == {"TTL": 654}


@mock_aws
def test_create_private_dns_namespace_with_duplicate_vpc():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_private_dns_namespace(Name="dns_ns", Vpc="vpc_id")

    with pytest.raises(ClientError) as exc:
        client.create_private_dns_namespace(Name="sth else", Vpc="vpc_id")
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictingDomainExists"


@mock_aws
def test_create_public_dns_namespace_minimal():
    client = boto3.client("servicediscovery", region_name="us-east-2")
    client.create_public_dns_namespace(Name="public_dns_ns")

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    assert "Namespace" in resp

    namespace = resp["Namespace"]
    assert re.match(ns_id, namespace["Id"])
    assert namespace["Name"] == "public_dns_ns"
    assert namespace["Type"] == "DNS_PUBLIC"


@mock_aws
def test_create_public_dns_namespace():
    client = boto3.client("servicediscovery", region_name="us-east-2")
    client.create_public_dns_namespace(
        Name="public_dns_ns",
        CreatorRequestId="cri",
        Description="my public dns",
        Properties={"DnsProperties": {"SOA": {"TTL": 124}}},
    )

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    assert "Namespace" in resp

    namespace = resp["Namespace"]
    assert re.match(ns_id, namespace["Id"])
    assert namespace["Name"] == "public_dns_ns"
    assert namespace["Type"] == "DNS_PUBLIC"
    assert namespace["Description"] == "my public dns"
    assert namespace["CreatorRequestId"] == "cri"

    assert "DnsProperties" in namespace["Properties"]
    dns_props = namespace["Properties"]["DnsProperties"]
    assert dns_props == {"HostedZoneId": "hzi", "SOA": {"TTL": 124}}


@mock_aws
def test_update_public_dns_namespace():
    client = boto3.client("servicediscovery", region_name="us-east-2")
    client.create_public_dns_namespace(
        Name="public_dns_ns",
        CreatorRequestId="cri",
        Description="my public dns",
        Properties={"DnsProperties": {"SOA": {"TTL": 124}}},
    )

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    client.update_public_dns_namespace(
        Id=ns_id,
        Namespace={
            "Description": "updated dns",
            "Properties": {"DnsProperties": {"SOA": {"TTL": 987}}},
        },
    )

    namespace = client.get_namespace(Id=ns_id)["Namespace"]
    assert namespace["Description"] == "updated dns"

    dns_props = namespace["Properties"]["DnsProperties"]
    assert dns_props == {"SOA": {"TTL": 987}}


@mock_aws
def test_update_http_namespace():
    client = boto3.client("servicediscovery", region_name="us-east-2")
    client.create_http_namespace(
        Name="mynamespace", CreatorRequestId="crid", Description="mu fancy namespace"
    )

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    client.update_http_namespace(
        Id=ns_id,
        Namespace={
            "Description": "updated http",
        },
    )

    namespace = client.get_namespace(Id=ns_id)["Namespace"]
    assert namespace["Description"] == "updated http"
