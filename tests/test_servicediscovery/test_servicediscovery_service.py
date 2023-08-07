"""Unit tests for servicediscovery-supported APIs."""
import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_servicediscovery

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_servicediscovery
def test_create_service_minimal():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    operation_id = client.create_http_namespace(Name="mynamespace")["OperationId"]
    namespace_id = client.get_operation(OperationId=operation_id)["Operation"][
        "Targets"
    ]["NAMESPACE"]

    resp = client.create_service(Name="my service", NamespaceId=namespace_id)

    assert "Service" in resp
    assert "Id" in resp["Service"]
    assert "Arn" in resp["Service"]
    assert resp["Service"]["Name"] == "my service"
    assert resp["Service"]["NamespaceId"] == namespace_id
    assert "CreateDate" in resp["Service"]


@mock_servicediscovery
def test_create_service():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    operation_id = client.create_http_namespace(Name="mynamespace")["OperationId"]
    namespace_id = client.get_operation(OperationId=operation_id)["Operation"][
        "Targets"
    ]["NAMESPACE"]

    resp = client.create_service(
        Name="my service",
        CreatorRequestId="crid",
        Description="my service",
        DnsConfig={
            "NamespaceId": namespace_id,
            "RoutingPolicy": "WEIGHTED",
            "DnsRecords": [{"Type": "SRV", "TTL": 0}],
        },
        HealthCheckConfig={"Type": "TCP", "ResourcePath": "/sth"},
        HealthCheckCustomConfig={"FailureThreshold": 125},
        Type="HTTP",
    )

    assert "Service" in resp
    assert "Id" in resp["Service"]
    assert "Arn" in resp["Service"]
    assert resp["Service"]["Name"] == "my service"
    assert "NamespaceId" not in resp["Service"]
    assert resp["Service"]["Description"] == "my service"
    assert resp["Service"]["DnsConfig"] == {
        "NamespaceId": namespace_id,
        "RoutingPolicy": "WEIGHTED",
        "DnsRecords": [{"Type": "SRV", "TTL": 0}],
    }
    assert resp["Service"]["HealthCheckConfig"] == {
        "Type": "TCP",
        "ResourcePath": "/sth",
    }
    assert resp["Service"]["HealthCheckCustomConfig"] == {"FailureThreshold": 125}
    assert resp["Service"]["Type"] == "HTTP"
    assert resp["Service"]["CreatorRequestId"] == "crid"


@mock_servicediscovery
def test_get_service():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")

    operation_id = client.create_http_namespace(Name="mynamespace")["OperationId"]
    namespace_id = client.get_operation(OperationId=operation_id)["Operation"][
        "Targets"
    ]["NAMESPACE"]

    service_id = client.create_service(Name="my service", NamespaceId=namespace_id)[
        "Service"
    ]["Id"]

    resp = client.get_service(Id=service_id)

    assert "Service" in resp
    assert "Id" in resp["Service"]
    assert "Arn" in resp["Service"]
    assert resp["Service"]["Name"] == "my service"
    assert resp["Service"]["NamespaceId"] == namespace_id


@mock_servicediscovery
def test_get_unknown_service():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_service(Id="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ServiceNotFound"
    assert err["Message"] == "unknown"


@mock_servicediscovery
def test_delete_service():
    client = boto3.client("servicediscovery", region_name="eu-west-1")

    operation_id = client.create_http_namespace(Name="mynamespace")["OperationId"]
    namespace_id = client.get_operation(OperationId=operation_id)["Operation"][
        "Targets"
    ]["NAMESPACE"]
    service_id = client.create_service(Name="my service", NamespaceId=namespace_id)[
        "Service"
    ]["Id"]

    client.delete_service(Id=service_id)

    with pytest.raises(ClientError) as exc:
        client.get_service(Id=service_id)
    err = exc.value.response["Error"]
    assert err["Code"] == "ServiceNotFound"
    assert err["Message"] == service_id


@mock_servicediscovery
def test_update_service_description():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    operation_id = client.create_http_namespace(Name="mynamespace")["OperationId"]
    namespace_id = client.get_operation(OperationId=operation_id)["Operation"][
        "Targets"
    ]["NAMESPACE"]

    service_id = client.create_service(
        Name="my service",
        NamespaceId=namespace_id,
        Description="first desc",
        DnsConfig={
            "NamespaceId": namespace_id,
            "RoutingPolicy": "WEIGHTED",
            "DnsRecords": [{"Type": "SRV", "TTL": 0}],
        },
        HealthCheckConfig={"Type": "TCP", "ResourcePath": "/sth"},
    )["Service"]["Id"]

    client.update_service(Id=service_id, Service={"Description": "updated desc"})

    resp = client.get_service(Id=service_id)

    assert "Service" in resp
    assert resp["Service"]["Id"] == service_id
    assert "Arn" in resp["Service"]
    assert resp["Service"]["Name"] == "my service"
    assert resp["Service"]["NamespaceId"] == namespace_id
    assert resp["Service"]["Description"] == "updated desc"
    # From the docs:
    #    If you omit any existing DnsRecords or HealthCheckConfig
    #    configurations from an UpdateService request,
    #    the configurations are deleted from the service.
    assert "DnsConfig" not in resp["Service"]
    assert resp["Service"]["HealthCheckConfig"] == {
        "Type": "TCP",
        "ResourcePath": "/sth",
    }


@mock_servicediscovery
def test_update_service_others():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")
    operation_id = client.create_http_namespace(Name="mynamespace")["OperationId"]
    namespace_id = client.get_operation(OperationId=operation_id)["Operation"][
        "Targets"
    ]["NAMESPACE"]

    service_id = client.create_service(
        Name="my service",
        NamespaceId=namespace_id,
        Description="first desc",
        DnsConfig={
            "RoutingPolicy": "WEIGHTED",
            "DnsRecords": [{"Type": "SRV", "TTL": 0}],
        },
    )["Service"]["Id"]

    client.update_service(
        Id=service_id,
        Service={
            "DnsConfig": {"DnsRecords": [{"Type": "SRV", "TTL": 12}]},
            "HealthCheckConfig": {"Type": "TCP", "ResourcePath": "/sth"},
        },
    )

    resp = client.get_service(Id=service_id)

    assert "Service" in resp
    assert resp["Service"]["Id"] == service_id
    assert "Arn" in resp["Service"]
    assert resp["Service"]["Name"] == "my service"
    assert resp["Service"]["NamespaceId"] == namespace_id
    assert resp["Service"]["Description"] == "first desc"
    assert resp["Service"]["DnsConfig"] == (
        {"RoutingPolicy": "WEIGHTED", "DnsRecords": [{"Type": "SRV", "TTL": 12}]}
    )
    assert resp["Service"]["HealthCheckConfig"] == {
        "Type": "TCP",
        "ResourcePath": "/sth",
    }
