import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
@mock_aws
def get_client():
    return boto3.client("vpc-lattice", region_name="ap-southeast-1")


@pytest.fixture(name="resource_groups_client")
@mock_aws
def get_resource_groups_client():
    return boto3.client("resourcegroupstaggingapi", region_name="ap-southeast-1")


@mock_aws
def test_vpc_lattice_service_tagging_api(client, resource_groups_client):
    tags = {"tag1": "value1", "tag2": "value2"}
    resp = client.create_service(name="my-service", authType="NONE", tags=tags)

    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[resp["arn"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == resp["arn"]
    assert resource_group_tags[0]["Tags"] == [
        {"Key": "tag1", "Value": "value1"},
        {"Key": "tag2", "Value": "value2"},
    ]


@mock_aws
def test_vpc_lattice_service_network_tagging_api(client, resource_groups_client):
    tags = {"tag1": "value1", "tag2": "value2"}
    resp = client.create_service_network(
        name="my-sn1",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
        tags=tags,
    )
    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[resp["arn"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert resource_group_tags[0]["ResourceARN"] == resp["arn"]
    assert resource_group_tags[0]["Tags"] == [
        {"Key": "tag1", "Value": "value1"},
        {"Key": "tag2", "Value": "value2"},
    ]
