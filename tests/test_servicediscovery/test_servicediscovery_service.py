"""Unit tests for servicediscovery-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
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

    resp.should.have.key("Service")
    resp["Service"].should.have.key("Id")
    resp["Service"].should.have.key("Arn")
    resp["Service"].should.have.key("Name").equals("my service")
    resp["Service"].should.have.key("NamespaceId").equals(namespace_id)
    resp["Service"].should.have.key("CreateDate")


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

    resp.should.have.key("Service")
    resp["Service"].should.have.key("Id")
    resp["Service"].should.have.key("Arn")
    resp["Service"].should.have.key("Name").equals("my service")
    resp["Service"].shouldnt.have.key("NamespaceId")
    resp["Service"].should.have.key("Description").equals("my service")
    resp["Service"].should.have.key("DnsConfig").equals(
        {
            "NamespaceId": namespace_id,
            "RoutingPolicy": "WEIGHTED",
            "DnsRecords": [{"Type": "SRV", "TTL": 0}],
        }
    )
    resp["Service"].should.have.key("HealthCheckConfig").equals(
        {"Type": "TCP", "ResourcePath": "/sth"}
    )
    resp["Service"].should.have.key("HealthCheckCustomConfig").equals(
        {"FailureThreshold": 125}
    )
    resp["Service"].should.have.key("Type").equals("HTTP")
    resp["Service"].should.have.key("CreatorRequestId").equals("crid")


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

    resp.should.have.key("Service")
    resp["Service"].should.have.key("Id")
    resp["Service"].should.have.key("Arn")
    resp["Service"].should.have.key("Name").equals("my service")
    resp["Service"].should.have.key("NamespaceId").equals(namespace_id)


@mock_servicediscovery
def test_get_unknown_service():
    client = boto3.client("servicediscovery", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.get_service(Id="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ServiceNotFound")
    err["Message"].should.equal("unknown")


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
    err["Code"].should.equal("ServiceNotFound")
    err["Message"].should.equal(service_id)


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

    resp.should.have.key("Service")
    resp["Service"].should.have.key("Id").equals(service_id)
    resp["Service"].should.have.key("Arn")
    resp["Service"].should.have.key("Name").equals("my service")
    resp["Service"].should.have.key("NamespaceId").equals(namespace_id)
    resp["Service"].should.have.key("Description").equals("updated desc")
    # From the docs:
    #    If you omit any existing DnsRecords or HealthCheckConfig configurations from an UpdateService request,
    #    the configurations are deleted from the service.
    resp["Service"].shouldnt.have.key("DnsConfig")
    resp["Service"].should.have.key("HealthCheckConfig").equals(
        {"Type": "TCP", "ResourcePath": "/sth"}
    )


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

    resp.should.have.key("Service")
    resp["Service"].should.have.key("Id").equals(service_id)
    resp["Service"].should.have.key("Arn")
    resp["Service"].should.have.key("Name").equals("my service")
    resp["Service"].should.have.key("NamespaceId").equals(namespace_id)
    resp["Service"].should.have.key("Description").equals("first desc")
    resp["Service"].should.have.key("DnsConfig").equals(
        {"RoutingPolicy": "WEIGHTED", "DnsRecords": [{"Type": "SRV", "TTL": 12}]}
    )
    resp["Service"].should.have.key("HealthCheckConfig").equals(
        {"Type": "TCP", "ResourcePath": "/sth"}
    )
