from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings


@pytest.fixture(name="client")
def client_fixture():
    with mock_aws():
        yield boto3.client("servicediscovery", region_name="eu-west-1")


@pytest.fixture(name="ns_resp")
def ns_resp_fixture(client):
    client.create_http_namespace(Name="mynamespace")
    namespace = [
        ns
        for ns in client.list_namespaces()["Namespaces"]
        if ns["Name"] == "mynamespace"
    ][0]
    return dict(Namespace=namespace)


@pytest.fixture(name="srv_resp")
def srv_resp_fixture(client, ns_resp):
    return client.create_service(
        Name="myservice",
        NamespaceId=ns_resp["Namespace"]["Id"],
        DnsConfig={"DnsRecords": [{"Type": "A", "TTL": 60}]},
    )


@mock_aws
def test_register_instance(client, ns_resp, srv_resp):
    instance_id = "i-123"
    creator_request_id = "crid"
    attributes = {"attr1": "value1"}
    inst_resp = client.register_instance(
        ServiceId=srv_resp["Service"]["Id"],
        InstanceId=instance_id,
        CreatorRequestId=creator_request_id,
        Attributes=attributes,
    )

    assert "OperationId" in inst_resp

    operation = client.get_operation(OperationId=inst_resp["OperationId"])
    assert operation["Operation"]["Targets"]["INSTANCE"] == instance_id

    instance = client.get_instance(
        ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id
    )
    assert instance["Instance"]["CreatorRequestId"] == creator_request_id
    assert instance["Instance"]["Attributes"] == attributes
    assert instance["Instance"]["Id"] == instance_id


@mock_aws
def test_deregister_instance(client, ns_resp, srv_resp):
    instance_id = "i-123"
    creator_request_id = "crid"
    attributes = {"attr1": "value1"}
    client.register_instance(
        ServiceId=srv_resp["Service"]["Id"],
        InstanceId=instance_id,
        CreatorRequestId=creator_request_id,
        Attributes=attributes,
    )

    dereg_resp = client.deregister_instance(
        ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id
    )
    assert "OperationId" in dereg_resp

    operation = client.get_operation(OperationId=dereg_resp["OperationId"])
    assert operation["Operation"]["Targets"]["INSTANCE"] == instance_id

    with pytest.raises(ClientError) as exc:
        client.get_instance(ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id)
        assert exc.value.response["Error"]["Code"] == "InstanceNotFound"
        assert exc.value.response["Error"]["Message"] == instance_id


@mock_aws
def test_get_instance(client, ns_resp, srv_resp):
    instance_id = "i-123"
    creator_request_id = "crid"
    attributes = {"attr1": "value1"}
    client.register_instance(
        ServiceId=srv_resp["Service"]["Id"],
        InstanceId=instance_id,
        CreatorRequestId=creator_request_id,
        Attributes=attributes,
    )

    instance = client.get_instance(
        ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id
    )
    assert "Instance" in instance
    assert instance["Instance"]["CreatorRequestId"] == creator_request_id
    assert instance["Instance"]["Attributes"] == attributes
    assert instance["Instance"]["Id"] == instance_id


@mock_aws
def test_get_unknown_instance(client, srv_resp):
    with pytest.raises(ClientError) as exc:
        client.get_instance(ServiceId=srv_resp["Service"]["Id"], InstanceId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "InstanceNotFound"
    assert err["Message"] == "unknown"


@mock_aws
def test_list_instances(client, ns_resp, srv_resp):
    instance_ids = ["i-123", "i-456", "i-789", "i-012"]
    for instance_id in instance_ids:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Attributes={}
        )

    instances = client.list_instances(ServiceId=srv_resp["Service"]["Id"])
    assert len(instances["Instances"]) == 4
    assert set(inst["Id"] for inst in instances["Instances"]) == set(instance_ids)


@mock_aws
def test_paginate_list_instances(client, ns_resp, srv_resp):
    instance_ids = ["i-123", "i-456", "i-789", "i-012"]
    for instance_id in instance_ids:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Attributes={}
        )

    instances = client.list_instances(ServiceId=srv_resp["Service"]["Id"], MaxResults=2)
    assert len(instances["Instances"]) == 2
    assert "NextToken" in instances
    assert set(inst["Id"] for inst in instances["Instances"]) == set(instance_ids[:2])

    instances = client.list_instances(
        ServiceId=srv_resp["Service"]["Id"], NextToken=instances["NextToken"]
    )
    assert len(instances["Instances"]) == 2
    assert "NextToken" not in instances
    assert set(inst["Id"] for inst in instances["Instances"]) == set(instance_ids[2:])


@mock_aws
def test_get_instances_health_status(client, ns_resp, srv_resp):
    instance_ids = ["i-123", "i-456", "i-789", "i-012"]
    for instance_id in instance_ids:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Attributes={}
        )

    health_status = client.get_instances_health_status(
        ServiceId=srv_resp["Service"]["Id"], Instances=instance_ids
    )
    assert len(health_status["Status"]) == 4
    for inst_id in instance_ids:
        assert health_status["Status"][inst_id] == "HEALTHY"


@mock_aws
def test_update_instance_custom_health_status(client, ns_resp, srv_resp):
    instance_id = "i-123"
    client.register_instance(
        ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Attributes={}
    )

    client.update_instance_custom_health_status(
        ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Status="UNHEALTHY"
    )

    health_status = client.get_instances_health_status(
        ServiceId=srv_resp["Service"]["Id"], Instances=[instance_id]
    )
    assert health_status["Status"][instance_id] == "UNHEALTHY"


@mock_aws
def test_discover_instances_formatting(client, ns_resp, srv_resp):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest(
            "Endpoint for discovering instances is prefixed with 'data-', and we can't intercept calls to 'data-localhost'"
        )

    attr_dict = {"attr1": "value1", "attr2": "value1"}
    client.register_instance(
        ServiceId=srv_resp["Service"]["Id"], InstanceId="i-123", Attributes=attr_dict
    )

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        MaxResults=2,
    )

    assert len(instances["Instances"]) == 1
    assert instances["Instances"][0]["InstanceId"] == "i-123"
    assert instances["Instances"][0]["NamespaceName"] == ns_resp["Namespace"]["Name"]
    assert instances["Instances"][0]["ServiceName"] == srv_resp["Service"]["Name"]
    assert instances["Instances"][0]["Attributes"] == attr_dict
    assert instances["Instances"][0]["HealthStatus"] == "HEALTHY"
    assert instances["InstancesRevision"] == 1


@mock_aws
def test_discover_instances_attr_filters(client, ns_resp, srv_resp):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest(
            "Endpoint for discovering instances is prefixed with 'data-', and we can't intercept calls to 'data-localhost'"
        )

    instance_dicts = [
        {"id": "i-123", "attributes": {"attr1": "value1", "attr2": "value1"}},
        {"id": "i-456", "attributes": {"attr1": "value2"}},
        {"id": "i-789", "attributes": {"attr1": "value3", "attr2": "value1"}},
        {"id": "i-012", "attributes": {"attr1": "value3"}},
    ]
    for inst_dict in instance_dicts:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"],
            InstanceId=inst_dict["id"],
            Attributes=inst_dict["attributes"],
        )

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
    )
    assert len(instances["Instances"]) == 4
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-123",
        "i-456",
        "i-789",
        "i-012",
    }

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        QueryParameters={"attr1": "value3"},
    )
    assert len(instances["Instances"]) == 2
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-789",
        "i-012",
    }

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        QueryParameters={"attr1": "value3"},
        OptionalParameters={"attr2": "value1"},
    )
    assert len(instances["Instances"]) == 1
    assert instances["Instances"][0]["InstanceId"] == "i-789"

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        QueryParameters={"attr1": "value3"},
        OptionalParameters={"attr2": "value2"},
    )
    assert len(instances["Instances"]) == 2
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-789",
        "i-012",
    }


@mock_aws
def test_discover_instances_health_filters(client, ns_resp, srv_resp):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest(
            "Endpoint for discovering instances is prefixed with 'data-', and we can't intercept calls to 'data-localhost'"
        )

    instance_dicts = [
        {"id": "i-123"},
        {"id": "i-456"},
        {"id": "i-789", "health": "UNHEALTHY"},
        {"id": "i-012", "health": "UNHEALTHY"},
    ]
    for inst_dict in instance_dicts:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"],
            InstanceId=inst_dict["id"],
            Attributes={},
        )
        if "health" in inst_dict:
            client.update_instance_custom_health_status(
                ServiceId=srv_resp["Service"]["Id"],
                InstanceId=inst_dict["id"],
                Status=inst_dict["health"],
            )

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        HealthStatus="ALL",
    )
    assert len(instances["Instances"]) == 4
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-123",
        "i-456",
        "i-789",
        "i-012",
    }

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        HealthStatus="UNHEALTHY",
    )
    assert len(instances["Instances"]) == 2
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-789",
        "i-012",
    }

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        HealthStatus="HEALTHY",
    )
    assert len(instances["Instances"]) == 2
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-123",
        "i-456",
    }

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        HealthStatus="HEALTHY_OR_ELSE_ALL",
    )
    assert len(instances["Instances"]) == 2
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-123",
        "i-456",
    }

    client.update_instance_custom_health_status(
        ServiceId=srv_resp["Service"]["Id"],
        InstanceId="i-123",
        Status="UNHEALTHY",
    )
    client.update_instance_custom_health_status(
        ServiceId=srv_resp["Service"]["Id"],
        InstanceId="i-456",
        Status="UNHEALTHY",
    )
    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        HealthStatus="HEALTHY_OR_ELSE_ALL",
    )
    assert len(instances["Instances"]) == 4
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == {
        "i-123",
        "i-456",
        "i-789",
        "i-012",
    }


@mock_aws
def test_max_results_discover_instances(client, ns_resp, srv_resp):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest(
            "Endpoint for discovering instances is prefixed with 'data-', and we can't intercept calls to 'data-localhost'"
        )

    instance_ids = ["i-123", "i-456", "i-789", "i-012"]
    for instance_id in instance_ids:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Attributes={}
        )

    instances = client.discover_instances(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
        MaxResults=2,
    )
    assert len(instances["Instances"]) == 2
    assert set(inst["InstanceId"] for inst in instances["Instances"]) == set(
        instance_ids[:2]
    )


@mock_aws
def test_discover_instances_revision(client, ns_resp, srv_resp):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest(
            "Endpoint for discovering instances is prefixed with 'data-', and we can't intercept calls to 'data-localhost'"
        )

    instance_ids = ["i-123", "i-456", "i-789", "i-012"]
    for instance_id in instance_ids:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Attributes={}
        )

    revisions = client.discover_instances_revision(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
    )
    assert revisions["InstancesRevision"] == 4

    client.deregister_instance(ServiceId=srv_resp["Service"]["Id"], InstanceId="i-123")
    client.register_instance(
        ServiceId=srv_resp["Service"]["Id"], InstanceId="i-123", Attributes={}
    )
    revisions = client.discover_instances_revision(
        NamespaceName=ns_resp["Namespace"]["Name"],
        ServiceName=srv_resp["Service"]["Name"],
    )
    assert revisions["InstancesRevision"] == 6
