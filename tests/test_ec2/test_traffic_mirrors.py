import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

REGION = "us-east-1"


@mock_aws
def test_create_traffic_mirror_filter():
    client = boto3.client("ec2", REGION)

    tags = [
        {"Key": "key1", "Value": "value1"},
        {"Key": "key2", "Value": "value2"},
    ]
    client_token = "test_token"
    response = client.create_traffic_mirror_filter(
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

    metadata = response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    traffic_mirror_filter = response["TrafficMirrorFilter"]
    assert "Description" in traffic_mirror_filter
    assert "TrafficMirrorFilterId" in traffic_mirror_filter
    assert response["ClientToken"] == client_token
    assert traffic_mirror_filter["Tags"] == tags


@mock_aws
def test_create_traffic_mirror_target():
    client = boto3.client("ec2", REGION)

    tags = [
        {"Key": "key1", "Value": "value1"},
        {"Key": "key2", "Value": "value2"},
    ]
    client_token = "test_token"
    network_interface_id = "test_network_interface_id"
    response = client.create_traffic_mirror_target(
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

    metadata = response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200
    assert metadata["RetryAttempts"] == 0

    traffic_mirror_target = response["TrafficMirrorTarget"]
    assert "Description" in traffic_mirror_target
    assert "TrafficMirrorTargetId" in traffic_mirror_target
    assert "Type" in traffic_mirror_target
    assert "OwnerId" in traffic_mirror_target
    assert response["ClientToken"] == client_token
    assert traffic_mirror_target["Tags"] == tags
    assert traffic_mirror_target["Type"] == "network-interface"


@mock_aws
def test_create_traffic_mirror_target_invalid_input():
    client = boto3.client("ec2", REGION)

    with pytest.raises(ClientError) as exc:
        client.create_traffic_mirror_target(
            NetworkInterfaceId="string", GatewayLoadBalancerEndpointId="string"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidInput"
    assert (
        err["Message"]
        == "Invalid number of inputs. Only 1 of NetworkInterfaceId, NetworkLoadBalancerArn or GatewayLoadBalancerEndpointId required."
    )


@mock_aws
def test_describe_traffic_mirror_filters():
    client = boto3.client("ec2", REGION)
    response = client.describe_traffic_mirror_filters()
    assert response["TrafficMirrorFilters"] == []


@mock_aws
def test_describe_traffic_mirror_filters_by_id():
    client = boto3.client("ec2", REGION)
    client.create_traffic_mirror_filter()
    client.create_traffic_mirror_filter()
    response = client.create_traffic_mirror_filter()

    traffic_mirror_filter_id = response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]
    described_traffic_mirrors = client.describe_traffic_mirror_filters(
        TrafficMirrorFilterIds=[traffic_mirror_filter_id]
    )["TrafficMirrorFilters"]

    assert len(described_traffic_mirrors) == 1
    my_traffic_mirror_filter = described_traffic_mirrors[0]
    assert my_traffic_mirror_filter["TrafficMirrorFilterId"] == traffic_mirror_filter_id


@mock_aws
def test_describe_traffic_mirror_targets():
    client = boto3.client("ec2", REGION)
    response = client.describe_traffic_mirror_targets()
    assert response["TrafficMirrorTargets"] == []


@mock_aws
def test_describe_traffic_mirror_targets_by_id():
    client = boto3.client("ec2", REGION)
    client.create_traffic_mirror_target(
        NetworkInterfaceId="test_network_interface_id_1"
    )
    client.create_traffic_mirror_target(
        NetworkInterfaceId="test_network_interface_id_2"
    )
    response = client.create_traffic_mirror_target(
        NetworkInterfaceId="test_network_interface_id_3"
    )

    traffic_mirror_target_id = response["TrafficMirrorTarget"]["TrafficMirrorTargetId"]
    described_traffic_mirrors = client.describe_traffic_mirror_targets(
        TrafficMirrorTargetIds=[traffic_mirror_target_id]
    )["TrafficMirrorTargets"]

    assert len(described_traffic_mirrors) == 1
    my_traffic_mirror_target = described_traffic_mirrors[0]
    assert my_traffic_mirror_target["TrafficMirrorTargetId"] == traffic_mirror_target_id
