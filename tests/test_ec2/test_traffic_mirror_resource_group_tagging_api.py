import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
@mock_aws
def get_client():
    return boto3.client("ec2", region_name="us-east-1")


@pytest.fixture(name="resource_groups_client")
@mock_aws
def get_resource_groups_client():
    return boto3.client("resourcegroupstaggingapi", region_name="us-east-1")


@mock_aws
def test_traffic_mirror_filter_tagging_api(client, resource_groups_client):
    tags = [
        {"Key": "key1", "Value": "value1"},
        {"Key": "key2", "Value": "value2"},
    ]
    client_token = "test_token"
    resp = client.create_traffic_mirror_filter(
        Description="test_description",
        TagSpecifications=[
            {
                "ResourceType": "traffic-mirror-filter",
                "Tags": tags,
            },
        ],
        ClientToken=client_token,
        DryRun=False,
    )

    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    traffic_mirror_filter = resp["TrafficMirrorFilter"]
    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[traffic_mirror_filter["TrafficMirrorFilterId"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert (
        traffic_mirror_filter["TrafficMirrorFilterId"]
        in resource_group_tags[0]["ResourceARN"]
    )
    assert resource_group_tags[0]["Tags"] == tags


@mock_aws
def test_traffic_mirror_target_tagging_api(client, resource_groups_client):
    tags = [
        {"Key": "key1", "Value": "value1"},
        {"Key": "key2", "Value": "value2"},
    ]
    client_token = "test_token"
    network_interface_id = "test_network_interface_id"
    resp = client.create_traffic_mirror_target(
        NetworkInterfaceId=network_interface_id,
        Description="test_description",
        TagSpecifications=[
            {
                "ResourceType": "traffic-mirror-target",
                "Tags": tags,
            },
        ],
        ClientToken=client_token,
        DryRun=False,
    )

    metadata = resp["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    traffic_mirror_target = resp["TrafficMirrorTarget"]
    resource_group_tags = resource_groups_client.get_resources(
        ResourceARNList=[traffic_mirror_target["TrafficMirrorTargetId"]],
    )["ResourceTagMappingList"]
    assert len(resource_group_tags) == 1
    assert (
        traffic_mirror_target["TrafficMirrorTargetId"]
        in resource_group_tags[0]["ResourceARN"]
    )
    assert resource_group_tags[0]["Tags"] == tags
