import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID

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
@pytest.mark.requires_clean_slate
def test_describe_traffic_mirror_filters():
    client = boto3.client("ec2", REGION)
    response = client.describe_traffic_mirror_filters()
    assert response["TrafficMirrorFilters"] == []


@mock_aws
def test_describe_traffic_mirror_filters_by_filtering():
    client = boto3.client("ec2", REGION)
    client.create_traffic_mirror_filter()
    client.create_traffic_mirror_filter()
    response = client.create_traffic_mirror_filter()

    traffic_mirror_filter_id = response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]

    filters = [
        {"Name": "traffic-mirror-filter-id", "Values": [traffic_mirror_filter_id]}
    ]

    described_traffic_mirrors = client.describe_traffic_mirror_filters(Filters=filters)[
        "TrafficMirrorFilters"
    ]

    assert len(described_traffic_mirrors) == 1
    my_traffic_mirror_filter = described_traffic_mirrors[0]
    assert my_traffic_mirror_filter["TrafficMirrorFilterId"] == traffic_mirror_filter_id


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
@pytest.mark.requires_clean_slate
def test_describe_traffic_mirror_targets():
    client = boto3.client("ec2", REGION)
    response = client.describe_traffic_mirror_targets()
    assert response["TrafficMirrorTargets"] == []


@mock_aws
def test_describe_traffic_mirror_targets_by_filtering():
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

    filters = [
        {"Name": "traffic-mirror-target-id", "Values": [traffic_mirror_target_id]}
    ]

    described_traffic_mirrors = client.describe_traffic_mirror_targets(Filters=filters)[
        "TrafficMirrorTargets"
    ]

    assert len(described_traffic_mirrors) == 1
    my_traffic_mirror_target = described_traffic_mirrors[0]
    assert my_traffic_mirror_target["TrafficMirrorTargetId"] == traffic_mirror_target_id


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


@mock_aws
def test_create_traffic_mirror_session():
    client = boto3.client("ec2", REGION)

    # Create required filter and target first
    filter_response = client.create_traffic_mirror_filter()
    filter_id = filter_response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]

    target_response = client.create_traffic_mirror_target(
        NetworkInterfaceId="eni-12345678"
    )
    target_id = target_response["TrafficMirrorTarget"]["TrafficMirrorTargetId"]

    tags = [
        {"Key": "key1", "Value": "value1"},
        {"Key": "key2", "Value": "value2"},
    ]
    client_token = "test_token"

    response = client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source123",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=1,
        PacketLength=100,
        VirtualNetworkId=12345,
        Description="test_description",
        TagSpecifications=[
            {
                "ResourceType": "traffic-mirror-session",
                "Tags": tags,
            },
        ],
        ClientToken=client_token,
    )

    metadata = response["ResponseMetadata"]
    assert metadata["HTTPStatusCode"] == 200

    session = response["TrafficMirrorSession"]
    assert "TrafficMirrorSessionId" in session
    assert session["TrafficMirrorSessionId"].startswith("tms-")
    assert session["TrafficMirrorTargetId"] == target_id
    assert session["TrafficMirrorFilterId"] == filter_id
    assert session["NetworkInterfaceId"] == "eni-source123"
    assert session["SessionNumber"] == 1
    assert session["PacketLength"] == 100
    assert session["VirtualNetworkId"] == 12345
    assert session["Description"] == "test_description"
    assert session["OwnerId"] == DEFAULT_ACCOUNT_ID
    assert response["ClientToken"] == client_token
    assert session["Tags"] == tags


@mock_aws
@pytest.mark.requires_clean_slate
def test_describe_traffic_mirror_sessions():
    client = boto3.client("ec2", REGION)
    response = client.describe_traffic_mirror_sessions()
    assert response["TrafficMirrorSessions"] == []


@mock_aws
def test_describe_traffic_mirror_sessions_by_id():
    client = boto3.client("ec2", REGION)

    # Create required filter and target
    filter_response = client.create_traffic_mirror_filter()
    filter_id = filter_response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]

    target_response = client.create_traffic_mirror_target(
        NetworkInterfaceId="eni-12345678"
    )
    target_id = target_response["TrafficMirrorTarget"]["TrafficMirrorTargetId"]

    # Create multiple sessions
    client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source1",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=1,
    )
    client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source2",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=2,
    )
    response = client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source3",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=3,
    )

    session_id = response["TrafficMirrorSession"]["TrafficMirrorSessionId"]
    described_sessions = client.describe_traffic_mirror_sessions(
        TrafficMirrorSessionIds=[session_id]
    )["TrafficMirrorSessions"]

    assert len(described_sessions) == 1
    assert described_sessions[0]["TrafficMirrorSessionId"] == session_id


@mock_aws
def test_describe_traffic_mirror_sessions_by_filtering():
    client = boto3.client("ec2", REGION)

    # Create required filter and target
    filter_response = client.create_traffic_mirror_filter()
    filter_id = filter_response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]

    target_response = client.create_traffic_mirror_target(
        NetworkInterfaceId="eni-12345678"
    )
    target_id = target_response["TrafficMirrorTarget"]["TrafficMirrorTargetId"]

    # Create multiple sessions
    client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source1",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=1,
    )
    response = client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source2",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=2,
    )

    session_id = response["TrafficMirrorSession"]["TrafficMirrorSessionId"]

    filters = [{"Name": "traffic-mirror-session-id", "Values": [session_id]}]
    described_sessions = client.describe_traffic_mirror_sessions(Filters=filters)[
        "TrafficMirrorSessions"
    ]

    assert len(described_sessions) == 1
    assert described_sessions[0]["TrafficMirrorSessionId"] == session_id


@mock_aws
def test_delete_traffic_mirror_session():
    client = boto3.client("ec2", REGION)

    # Create required filter and target
    filter_response = client.create_traffic_mirror_filter()
    filter_id = filter_response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]

    target_response = client.create_traffic_mirror_target(
        NetworkInterfaceId="eni-12345678"
    )
    target_id = target_response["TrafficMirrorTarget"]["TrafficMirrorTargetId"]

    # Create a session
    create_response = client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source1",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=1,
    )
    session_id = create_response["TrafficMirrorSession"]["TrafficMirrorSessionId"]

    # Delete the session
    delete_response = client.delete_traffic_mirror_session(
        TrafficMirrorSessionId=session_id
    )
    assert delete_response["TrafficMirrorSessionId"] == session_id

    # Verify it's gone
    described = client.describe_traffic_mirror_sessions(
        TrafficMirrorSessionIds=[session_id]
    )["TrafficMirrorSessions"]
    assert len(described) == 0


@mock_aws
def test_modify_traffic_mirror_session():
    client = boto3.client("ec2", REGION)

    # Create required filter and target
    filter_response = client.create_traffic_mirror_filter()
    filter_id = filter_response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]

    target_response = client.create_traffic_mirror_target(
        NetworkInterfaceId="eni-12345678"
    )
    target_id = target_response["TrafficMirrorTarget"]["TrafficMirrorTargetId"]

    # Create a session
    create_response = client.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source1",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=1,
        Description="original",
    )
    session_id = create_response["TrafficMirrorSession"]["TrafficMirrorSessionId"]

    # Modify the session
    modify_response = client.modify_traffic_mirror_session(
        TrafficMirrorSessionId=session_id,
        Description="modified",
        SessionNumber=99,
        PacketLength=200,
        VirtualNetworkId=54321,
    )

    modified_session = modify_response["TrafficMirrorSession"]
    assert modified_session["Description"] == "modified"
    assert modified_session["SessionNumber"] == 99
    assert modified_session["PacketLength"] == 200
    assert modified_session["VirtualNetworkId"] == 54321


@mock_aws
def test_traffic_mirror_session_tags_via_rgta():
    """Test that traffic mirror session tags surface through Resource Groups Tagging API."""
    ec2 = boto3.client("ec2", REGION)
    rgta = boto3.client("resourcegroupstaggingapi", REGION)

    # Create required filter and target
    filter_response = ec2.create_traffic_mirror_filter()
    filter_id = filter_response["TrafficMirrorFilter"]["TrafficMirrorFilterId"]

    target_response = ec2.create_traffic_mirror_target(
        NetworkInterfaceId="eni-12345678"
    )
    target_id = target_response["TrafficMirrorTarget"]["TrafficMirrorTargetId"]

    tags = [
        {"Key": "ASV", "Value": "test-asv"},
        {"Key": "BA", "Value": "test-ba"},
        {"Key": "OwnerContact", "Value": "test@example.com"},
    ]

    # Create a session with tags
    create_response = ec2.create_traffic_mirror_session(
        NetworkInterfaceId="eni-source1",
        TrafficMirrorTargetId=target_id,
        TrafficMirrorFilterId=filter_id,
        SessionNumber=1,
        TagSpecifications=[
            {
                "ResourceType": "traffic-mirror-session",
                "Tags": tags,
            },
        ],
    )
    session_id = create_response["TrafficMirrorSession"]["TrafficMirrorSessionId"]

    # Query via RGTA
    resources = rgta.get_resources(ResourceTypeFilters=["ec2:traffic-mirror-session"])[
        "ResourceTagMappingList"
    ]

    # Find our session
    session_resources = [r for r in resources if session_id in r["ResourceARN"]]
    assert len(session_resources) == 1

    resource = session_resources[0]
    assert f"traffic-mirror-session/{session_id}" in resource["ResourceARN"]

    # Verify tags
    tag_map = {t["Key"]: t["Value"] for t in resource["Tags"]}
    assert tag_map["ASV"] == "test-asv"
    assert tag_map["BA"] == "test-ba"
    assert tag_map["OwnerContact"] == "test@example.com"
