import re

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_list_operations_initial():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.list_operations()

    assert resp["Operations"] == []


@mock_aws
def test_list_operations():
    client = boto3.client("servicediscovery", region_name="eu-west-2")

    resp = client.create_http_namespace(Name="n/a")
    assert "OperationId" in resp
    op_id = resp["OperationId"]

    resp = client.list_operations()
    assert len(resp["Operations"]) == 1
    assert resp["Operations"] == [{"Id": op_id, "Status": "SUCCESS"}]


@mock_aws
def test_get_create_http_namespace_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.create_http_namespace(Name="mynamespace")

    assert re.match("[a-z0-9]{32}-[a-z0-9]{8}", resp["OperationId"])

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    assert "Operation" in resp
    operation = resp["Operation"]
    assert operation["Id"] == operation_id
    assert operation["Type"] == "CREATE_NAMESPACE"
    assert operation["Status"] == "SUCCESS"
    assert "CreateDate" in operation
    assert "UpdateDate" in operation
    assert "Targets" in operation

    targets = operation["Targets"]
    assert "NAMESPACE" in targets

    namespaces = client.list_namespaces()["Namespaces"]
    assert targets["NAMESPACE"] in [ns["Id"] for ns in namespaces]


@mock_aws
def test_get_private_dns_namespace_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.create_private_dns_namespace(Name="dns_ns", Vpc="vpc_id")

    assert re.match("[a-z0-9]{32}-[a-z0-9]{8}", resp["OperationId"])

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    assert "Operation" in resp
    operation = resp["Operation"]
    assert operation["Id"] == operation_id
    assert operation["Type"] == "CREATE_NAMESPACE"
    assert operation["Status"] == "SUCCESS"
    assert "CreateDate" in operation
    assert "UpdateDate" in operation
    assert "Targets" in operation


@mock_aws
def test_get_public_dns_namespace_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    resp = client.create_public_dns_namespace(Name="dns_ns")

    assert re.match("[a-z0-9]{32}-[a-z0-9]{8}", resp["OperationId"])

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    assert "Operation" in resp
    operation = resp["Operation"]
    assert operation["Id"] == operation_id
    assert operation["Type"] == "CREATE_NAMESPACE"
    assert operation["Status"] == "SUCCESS"
    assert "CreateDate" in operation
    assert "UpdateDate" in operation
    assert "Targets" in operation


@mock_aws
def test_get_update_service_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")
    service_id = client.create_service(
        Name="my service", NamespaceId="ns_id", Description="first desc"
    )["Service"]["Id"]

    resp = client.update_service(Id=service_id, Service={"Description": "updated desc"})

    assert re.match("[a-z0-9]{32}-[a-z0-9]{8}", resp["OperationId"])

    operation_id = resp["OperationId"]

    resp = client.get_operation(OperationId=operation_id)

    assert "Operation" in resp
    operation = resp["Operation"]
    assert operation["Id"] == operation_id
    assert operation["Type"] == "UPDATE_SERVICE"
    assert operation["Status"] == "SUCCESS"
    assert "CreateDate" in operation
    assert "UpdateDate" in operation
    assert "Targets" in operation


@mock_aws
def test_get_unknown_operation():
    client = boto3.client("servicediscovery", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_operation(OperationId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "OperationNotFound"
