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


@mock_aws
def test_vpc_lattice_snva_tagging_api(client, resource_groups_client):
    tags = {"tag1": "value1", "tag2": "value2"}
    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )
    resp = client.create_service_network_vpc_association(
        serviceNetworkIdentifier=resp_sn["id"],
        vpcIdentifier="vpc-12345678",
        securityGroupIds=["sg-12345678"],
        clientToken="token456",
        tags=tags,
    )

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
def test_vpc_lattice_rule_tagging_api(client, resource_groups_client):
    tags = {"tag1": "value1", "tag2": "value2"}
    resp_svc = client.create_service(
        name="my-service",
        authType="NONE",
    )

    resp = client.create_rule(
        listenerIdentifier="listener-1234567890123456",
        serviceIdentifier=resp_svc["id"],
        name="my-rule",
        priority=1,
        match={
            "httpMatch": {
                "pathMatch": {"caseSensitive": False, "match": {"exact": "/my-path"}}
            }
        },
        action={
            "forward": {
                "targetGroups": [{"targetGroupIdentifier": "tg-1234567890abcdef"}]
            }
        },
        clientToken="token789",
        tags=tags,
    )

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
def test_vpc_lattice_als_tagging_api(client, resource_groups_client):
    tags = {"tag1": "value1", "tag2": "value2"}
    resp_sn = client.create_service_network(
        name="my-sn",
        authType="NONE",
        clientToken="token123",
        sharingConfig={"enabled": False},
    )

    resp = client.create_access_log_subscription(
        resourceIdentifier=resp_sn["id"],
        destinationArn="arn:aws:s3:::my-log-bucket",
        clientToken="token456",
        serviceNetworkLogType="RESOURCE",
        tags=tags,
    )

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
def test_vpc_lattice_tag_filtering(client, resource_groups_client):
    # WITH tags
    tags1 = {"tag1": "value1"}

    svc1 = client.create_service(name="svc-yes", authType="NONE", tags=tags1)

    sn1 = client.create_service_network(name="sn-yes", authType="NONE", tags=tags1)

    snva1 = client.create_service_network_vpc_association(
        serviceNetworkIdentifier=sn1["id"],
        vpcIdentifier="vpc-1",
        tags=tags1,
    )

    rule1 = client.create_rule(
        listenerIdentifier="listener-1234567890123456",
        serviceIdentifier=svc1["id"],
        name="rule-yes",
        priority=1,
        match={
            "httpMatch": {
                "pathMatch": {"caseSensitive": False, "match": {"exact": "/my-path"}}
            }
        },
        action={
            "forward": {
                "targetGroups": [{"targetGroupIdentifier": "tg-1234567890abcdef"}]
            }
        },
        tags=tags1,
    )

    als1 = client.create_access_log_subscription(
        resourceIdentifier=sn1["id"],
        destinationArn="arn:aws:s3:::my-log-bucket1",
        serviceNetworkLogType="RESOURCE",
        tags=tags1,
    )

    # WITHOUT tags
    svc2 = client.create_service(name="svc-no", authType="NONE")

    sn2 = client.create_service_network(name="sn-no", authType="NONE")

    client.create_service_network_vpc_association(
        serviceNetworkIdentifier=sn2["id"],
        vpcIdentifier="vpc-2",
    )

    client.create_rule(
        listenerIdentifier="listener-1234567890123456",
        serviceIdentifier=svc2["id"],
        name="rule-no",
        priority=2,
        match={
            "httpMatch": {
                "pathMatch": {"caseSensitive": False, "match": {"exact": "/no"}}
            }
        },
        action={
            "forward": {
                "targetGroups": [{"targetGroupIdentifier": "tg-2234567890abcdef"}]
            }
        },
    )

    client.create_access_log_subscription(
        resourceIdentifier=sn2["id"],
        destinationArn="arn:aws:s3:::my-log-bucket2",
        serviceNetworkLogType="RESOURCE",
    )

    # Query TagFilter
    res_match = resource_groups_client.get_resources(
        ResourceTypeFilters=["vpc-lattice"],
        TagFilters=[{"Key": "tag1", "Values": ["value1"]}],
    )["ResourceTagMappingList"]
    arns_match = [r["ResourceARN"] for r in res_match]
    assert len(res_match) == 5
    assert svc1["arn"] in arns_match
    assert sn1["arn"] in arns_match
    assert snva1["arn"] in arns_match
    assert rule1["arn"] in arns_match
    assert als1["arn"] in arns_match

    # Query TagFilter NOT matching
    res_nomatch = resource_groups_client.get_resources(
        ResourceTypeFilters=["vpc-lattice"],
        TagFilters=[{"Key": "tag1", "Values": ["wrong"]}],
    )["ResourceTagMappingList"]
    assert len(res_nomatch) == 0
