"""Unit tests for servicediscovery-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_servicediscovery

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_servicediscovery
def test_list_operations_initial():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.list_operations()

    resp.should.have.key("Operations").equals([])


@mock_servicediscovery
def test_list_operations():
    client = boto3.client("servicediscovery", region_name="eu-west-2")

    resp = client.create_http_namespace(Name="n/a")
    resp.should.have.key("OperationId")
    op_id = resp["OperationId"]

    resp = client.list_operations()
    resp.should.have.key("Operations").length_of(1)
    resp["Operations"].should.equal([{"Id": op_id, "Status": "SUCCESS"}])


@mock_servicediscovery
def test_get_create_http_namespace_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.create_http_namespace(Name="mynamespace")

    resp["OperationId"].should.match("[a-z0-9]{32}-[a-z0-9]{8}")

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    resp.should.have.key("Operation")
    operation = resp["Operation"]
    operation.should.have.key("Id").equals(operation_id)
    operation.should.have.key("Type").equals("CREATE_NAMESPACE")
    operation.should.have.key("Status").equals("SUCCESS")
    operation.should.have.key("CreateDate")
    operation.should.have.key("UpdateDate")
    operation.should.have.key("Targets")

    targets = operation["Targets"]
    targets.should.have.key("NAMESPACE")

    namespaces = client.list_namespaces()["Namespaces"]
    [ns["Id"] for ns in namespaces].should.contain(targets["NAMESPACE"])


@mock_servicediscovery
def test_get_private_dns_namespace_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.create_private_dns_namespace(Name="dns_ns", Vpc="vpc_id")

    resp["OperationId"].should.match("[a-z0-9]{32}-[a-z0-9]{8}")

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    resp.should.have.key("Operation")
    operation = resp["Operation"]
    operation.should.have.key("Id").equals(operation_id)
    operation.should.have.key("Type").equals("CREATE_NAMESPACE")
    operation.should.have.key("Status").equals("SUCCESS")
    operation.should.have.key("CreateDate")
    operation.should.have.key("UpdateDate")
    operation.should.have.key("Targets")


@mock_servicediscovery
def test_get_public_dns_namespace_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.create_public_dns_namespace(Name="dns_ns")

    resp["OperationId"].should.match("[a-z0-9]{32}-[a-z0-9]{8}")

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    resp.should.have.key("Operation")
    operation = resp["Operation"]
    operation.should.have.key("Id").equals(operation_id)
    operation.should.have.key("Type").equals("CREATE_NAMESPACE")
    operation.should.have.key("Status").equals("SUCCESS")
    operation.should.have.key("CreateDate")
    operation.should.have.key("UpdateDate")
    operation.should.have.key("Targets")


@mock_servicediscovery
def test_get_update_service_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    service_id = client.create_service(
        Name="my service", NamespaceId="ns_id", Description="first desc"
    )["Service"]["Id"]

    resp = client.update_service(Id=service_id, Service={"Description": "updated desc"})

    resp["OperationId"].should.match("[a-z0-9]{32}-[a-z0-9]{8}")

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    resp.should.have.key("Operation")
    operation = resp["Operation"]
    operation.should.have.key("Id").equals(operation_id)
    operation.should.have.key("Type").equals("UPDATE_SERVICE")
    operation.should.have.key("Status").equals("SUCCESS")
    operation.should.have.key("CreateDate")
    operation.should.have.key("UpdateDate")
    operation.should.have.key("Targets")


@mock_servicediscovery
def test_get_unknown_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_operation(OperationId="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("OperationNotFound")
