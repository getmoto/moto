import boto3
import pytest

from moto import mock_aws


@pytest.fixture(name="client")
@mock_aws
def get_client():
    return boto3.client("dms", region_name="us-east-1")


@pytest.fixture(name="resource_groups_client")
@mock_aws
def get_resource_groups_client():
    return boto3.client("resourcegroupstaggingapi", region_name="us-east-1")


@mock_aws
def test_create_replication_task_with_tags(client, resource_groups_client):
    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
        ReplicationTaskSettings='{"Logging":{} }',
        Tags=[
            {"Key": "Test-tag", "Value": "Test Task"},
            {"Key": "Test-tag2", "Value": "Test Task"},
        ],
    )

    task1 = response["ReplicationTask"]

    client.create_replication_task(
        ReplicationTaskIdentifier="test-untagged",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
        ReplicationTaskSettings='{"Logging":{} }',
    )

    tasks = client.describe_replication_tasks(
        Filters=[
            {
                "Name": "replication-instance-arn",
                "Values": ["replication-instance-arn"],
            },
        ]
    )

    assert len(tasks["ReplicationTasks"]) == 2

    response_no_filter = resource_groups_client.get_resources(
        ResourceTypeFilters=["dms:task"]
    )
    assert len(response_no_filter["ResourceTagMappingList"]) == 2

    response_filtered = resource_groups_client.get_resources(
        ResourceTypeFilters=["dms:task"],
        TagFilters=[{"Key": "Test-tag", "Values": ["Test Task"]}],
    )
    assert len(response_filtered["ResourceTagMappingList"]) == 1
    resources = response_filtered["ResourceTagMappingList"]
    assert resources[0]["ResourceARN"] == task1["ReplicationTaskArn"]
    assert resources[0]["Tags"] == [
        {"Key": "Test-tag", "Value": "Test Task"},
        {"Key": "Test-tag2", "Value": "Test Task"},
    ]


@mock_aws
def test_tag_and_untag_replication_task(client, resource_groups_client):
    task_arn = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
        ReplicationTaskSettings='{"Logging":{} }',
        Tags=[{"Key": "Test", "Value": "1"}],
    )["ReplicationTask"]["ReplicationTaskArn"]

    # Basic test
    resp = resource_groups_client.get_resources(ResourceTypeFilters=["dms:task"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == task_arn
    assert resp["ResourceTagMappingList"][0]["Tags"] == [{"Key": "Test", "Value": "1"}]

    # Add a tag through the Resource Groups Tagging API
    failed = resource_groups_client.tag_resources(
        ResourceARNList=[task_arn],
        Tags={"Test2": "2"},
    )
    assert failed["FailedResourcesMap"] == {}

    resp = resource_groups_client.get_resources(ResourceTypeFilters=["dms:task"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert {"Key": "Test", "Value": "1"} in tags
    assert {"Key": "Test2", "Value": "2"} in tags

    # Filtering on the newly-added tag returns the task
    resp = resource_groups_client.get_resources(
        ResourceTypeFilters=["dms:task"],
        TagFilters=[{"Key": "Test2", "Values": ["2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert resp["ResourceTagMappingList"][0]["ResourceARN"] == task_arn

    # Remove the original tag through the Resource Groups Tagging API
    failed = resource_groups_client.untag_resources(
        ResourceARNList=[task_arn],
        TagKeys=["Test"],
    )
    assert failed["FailedResourcesMap"] == {}

    resp = resource_groups_client.get_resources(ResourceTypeFilters=["dms:task"])
    tags = resp["ResourceTagMappingList"][0]["Tags"]
    assert tags == [{"Key": "Test2", "Value": "2"}]

    # The removed tag no longer matches
    resp = resource_groups_client.get_resources(
        ResourceTypeFilters=["dms:task"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
