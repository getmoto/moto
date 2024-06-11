import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@pytest.fixture(scope="module")
def client():
    with mock_aws():
        yield boto3.client("servicediscovery", region_name="eu-west-1")


@pytest.fixture(scope="module")
def ns_resp(client):
    return client.create_private_dns_namespace(Name="mynamespace")


@pytest.fixture(scope="module")
def srv_resp(client, ns_resp):
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
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id
        )

    instances = client.list_instances(ServiceId=srv_resp["Service"]["Id"])
    assert len(instances["Instances"]) == 4
    assert set(inst["Id"] for inst in instances["Instances"]) == set(instance_ids)


@mock_aws
def test_paginate_list_instances(client, ns_resp, srv_resp):
    instance_ids = ["i-123", "i-456", "i-789", "i-012"]
    for instance_id in instance_ids:
        client.register_instance(
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id
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
            ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id
        )

    health_status = client.get_instances_health_status(
        ServiceId=srv_resp["Service"]["Id"]
    )
    assert len(health_status["Status"]) == 4
    for inst_id in instance_ids:
        assert health_status["Status"][inst_id] == "HEALTHY"


@mock_aws
def test_update_instance_custom_health_status(client, ns_resp, srv_resp):
    instance_id = "i-123"
    client.register_instance(
        ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id
    )

    client.update_instance_custom_health_status(
        ServiceId=srv_resp["Service"]["Id"], InstanceId=instance_id, Status="UNHEALTHY"
    )

    health_status = client.get_instances_health_status(
        ServiceId=srv_resp["Service"]["Id"]
    )
    assert health_status["Status"][instance_id] == "UNHEALTHY"
