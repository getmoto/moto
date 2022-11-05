"""Unit tests for servicediscovery-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_servicediscovery
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_servicediscovery
def test_create_http_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(Name="mynamespace")

    resp = client.list_namespaces()
    resp.should.have.key("Namespaces").length_of(1)

    namespace = resp["Namespaces"][0]
    namespace.should.have.key("Id").match("ns-[a-z0-9]{16}")
    namespace.should.have.key("Arn").match(
        f"arn:aws:servicediscovery:eu-west-1:{ACCOUNT_ID}:namespace/{namespace['Id']}"
    )
    namespace.should.have.key("Name").equals("mynamespace")
    namespace.should.have.key("Type").equals("HTTP")
    namespace.should.have.key("CreateDate")

    namespace.should.have.key("Properties")
    props = namespace["Properties"]
    props.should.have.key("DnsProperties").equals({"SOA": {}})
    props.should.have.key("HttpProperties").equals({"HttpName": "mynamespace"})


@mock_servicediscovery
def test_get_http_namespace_minimal():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(Name="mynamespace")

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    resp.should.have.key("Namespace")

    namespace = resp["Namespace"]
    namespace.should.have.key("Id").match(ns_id)
    namespace.should.have.key("Arn").match(
        f"arn:aws:servicediscovery:eu-west-1:{ACCOUNT_ID}:namespace/{namespace['Id']}"
    )
    namespace.should.have.key("Name").equals("mynamespace")
    namespace.should.have.key("Type").equals("HTTP")
    namespace.should.have.key("CreateDate")
    namespace.should.have.key("CreatorRequestId")

    namespace.should.have.key("Properties")
    props = namespace["Properties"]
    props.should.have.key("DnsProperties").equals({"SOA": {}})
    props.should.have.key("HttpProperties").equals({"HttpName": "mynamespace"})

    namespace.shouldnt.have.key("Description")


@mock_servicediscovery
def test_get_http_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(
        Name="mynamespace", CreatorRequestId="crid", Description="mu fancy namespace"
    )

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    resp.should.have.key("Namespace")

    namespace = resp["Namespace"]
    namespace.should.have.key("Id").match(ns_id)
    namespace.should.have.key("Arn").match(
        f"arn:aws:servicediscovery:eu-west-1:{ACCOUNT_ID}:namespace/{namespace['Id']}"
    )
    namespace.should.have.key("Name").equals("mynamespace")
    namespace.should.have.key("Type").equals("HTTP")
    namespace.should.have.key("CreateDate")
    namespace.should.have.key("CreatorRequestId").equals("crid")
    namespace.should.have.key("Description").equals("mu fancy namespace")

    namespace.should.have.key("Properties")
    props = namespace["Properties"]
    props.should.have.key("DnsProperties").equals({"SOA": {}})
    props.should.have.key("HttpProperties").equals({"HttpName": "mynamespace"})


@mock_servicediscovery
def test_delete_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_http_namespace(Name="mynamespace")
    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.delete_namespace(Id=ns_id)
    resp.should.have.key("OperationId")

    # Calling delete again while this is in progress results in an error:
    #    Another operation of type DeleteNamespace and id dlmpkcn33aovnztwdpsdplgtheuhgcap-k6x64euq is in progress
    # list_operations is empty after successfull deletion - old operations from this namespace should be deleted
    # list_namespaces is also empty (obvs)

    client.list_namespaces()["Namespaces"].should.equal([])
    client.list_operations()["Operations"].should.equal([])


@mock_servicediscovery
def test_delete_unknown_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.delete_namespace(Id="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NamespaceNotFound")
    err["Message"].should.equal("unknown")


@mock_servicediscovery
def test_get_unknown_namespace():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.get_namespace(Id="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NamespaceNotFound")
    err["Message"].should.equal("unknown")


@mock_servicediscovery
def test_create_private_dns_namespace_minimal():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_private_dns_namespace(Name="dns_ns", Vpc="vpc_id")

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    resp.should.have.key("Namespace")

    namespace = resp["Namespace"]
    namespace.should.have.key("Id").match(ns_id)
    namespace.should.have.key("Name").equals("dns_ns")
    namespace.should.have.key("Type").equals("DNS_PRIVATE")

    namespace.should.have.key("Properties")
    props = namespace["Properties"]
    props.should.have.key("DnsProperties")
    props["DnsProperties"].should.have.key("HostedZoneId")
    props["DnsProperties"].shouldnt.have.key("SOA")


@mock_servicediscovery
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
    resp.should.have.key("Namespace")

    namespace = resp["Namespace"]
    namespace.should.have.key("Id").match(ns_id)
    namespace.should.have.key("Name").equals("dns_ns")
    namespace.should.have.key("Type").equals("DNS_PRIVATE")
    namespace.should.have.key("Description").equals("my private dns")

    namespace.should.have.key("Properties")
    props = namespace["Properties"]
    props.should.have.key("DnsProperties")
    props["DnsProperties"].should.have.key("HostedZoneId")
    props["DnsProperties"].should.have.key("SOA").equals({"TTL": 123})


@mock_servicediscovery
def test_create_private_dns_namespace_with_duplicate_vpc():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    client.create_private_dns_namespace(Name="dns_ns", Vpc="vpc_id")

    with pytest.raises(ClientError) as exc:
        client.create_private_dns_namespace(Name="sth else", Vpc="vpc_id")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ConflictingDomainExists")


@mock_servicediscovery
def test_create_public_dns_namespace_minimal():
    client = boto3.client("servicediscovery", region_name="us-east-2")
    client.create_public_dns_namespace(Name="public_dns_ns")

    ns_id = client.list_namespaces()["Namespaces"][0]["Id"]

    resp = client.get_namespace(Id=ns_id)
    resp.should.have.key("Namespace")

    namespace = resp["Namespace"]
    namespace.should.have.key("Id").match(ns_id)
    namespace.should.have.key("Name").equals("public_dns_ns")
    namespace.should.have.key("Type").equals("DNS_PUBLIC")


@mock_servicediscovery
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
    resp.should.have.key("Namespace")

    namespace = resp["Namespace"]
    namespace.should.have.key("Id").match(ns_id)
    namespace.should.have.key("Name").equals("public_dns_ns")
    namespace.should.have.key("Type").equals("DNS_PUBLIC")
    namespace.should.have.key("Description").equals("my public dns")
    namespace.should.have.key("CreatorRequestId").equals("cri")

    namespace.should.have.key("Properties").should.have.key("DnsProperties")
    dns_props = namespace["Properties"]["DnsProperties"]
    dns_props.should.equal({"HostedZoneId": "hzi", "SOA": {"TTL": 124}})
