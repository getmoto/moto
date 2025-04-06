import json

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_and_get_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
        ReplicationTaskSettings='{"Logging":{} }',
    )

    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-id", "Values": ["test"]}]
    )

    assert len(tasks["ReplicationTasks"]) == 1
    task = tasks["ReplicationTasks"][0]
    assert task["ReplicationTaskIdentifier"] == "test"
    assert task["SourceEndpointArn"] == "source-endpoint-arn"
    assert task["TargetEndpointArn"] == "target-endpoint-arn"
    assert task["ReplicationInstanceArn"] == "replication-instance-arn"
    assert task["MigrationType"] == "full-load"
    assert task["Status"] == "creating"
    assert task["TableMappings"] == '{"rules":[]}'
    assert isinstance(json.loads(task["TableMappings"]), dict)

    assert task["ReplicationTaskSettings"] == '{"Logging":{} }'
    assert isinstance(json.loads(task["ReplicationTaskSettings"]), dict)


@mock_aws
def test_create_existing_replication_task_throws_error():
    client = boto3.client("dms", region_name="us-east-1")

    client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )

    with pytest.raises(ClientError) as ex:
        client.create_replication_task(
            ReplicationTaskIdentifier="test",
            SourceEndpointArn="source-endpoint-arn",
            TargetEndpointArn="target-endpoint-arn",
            ReplicationInstanceArn="replication-instance-arn",
            MigrationType="full-load",
            TableMappings='{"rules":[]}',
        )

    assert ex.value.operation_name == "CreateReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceAlreadyExistsFault"
    assert (
        ex.value.response["Error"]["Message"]
        == "The resource you are attempting to create already exists."
    )


@mock_aws
def test_start_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
    client.start_replication_task(
        ReplicationTaskArn=task_arn, StartReplicationTaskType="start-replication"
    )
    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn]}]
    )

    assert tasks["ReplicationTasks"][0]["Status"] == "running"


@mock_aws
def test_start_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.start_replication_task(
            ReplicationTaskArn="does-not-exist",
            StartReplicationTaskType="start-replication",
        )

    assert ex.value.operation_name == "StartReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"] == "Replication task could not be found."
    )


@mock_aws
def test_stop_replication_task_throws_invalid_state_error():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]

    with pytest.raises(ClientError) as ex:
        client.stop_replication_task(ReplicationTaskArn=task_arn)

    assert ex.value.operation_name == "StopReplicationTask"
    assert ex.value.response["Error"]["Code"] == "InvalidResourceStateFault"
    assert ex.value.response["Error"]["Message"] == "Replication task is not running"


@mock_aws
def test_stop_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.stop_replication_task(ReplicationTaskArn="does-not-exist")

    assert ex.value.operation_name == "StopReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"] == "Replication task could not be found."
    )


@mock_aws
def test_stop_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
    client.start_replication_task(
        ReplicationTaskArn=task_arn, StartReplicationTaskType="start-replication"
    )
    client.stop_replication_task(ReplicationTaskArn=task_arn)
    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn]}]
    )

    assert tasks["ReplicationTasks"][0]["Status"] == "stopped"


@mock_aws
def test_delete_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )
    task_arn = response["ReplicationTask"]["ReplicationTaskArn"]
    client.delete_replication_task(ReplicationTaskArn=task_arn)
    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn]}]
    )

    assert len(tasks["ReplicationTasks"]) == 0


@mock_aws
def test_delete_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_replication_task(ReplicationTaskArn="does-not-exist")

    assert ex.value.operation_name == "DeleteReplicationTask"
    assert ex.value.response["Error"]["Code"] == "ResourceNotFoundFault"
    assert (
        ex.value.response["Error"]["Message"] == "Replication task could not be found."
    )


@mock_aws
def test_create_replication_instance():
    client = boto3.client("dms", region_name="us-east-1")

    response = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance",
        ReplicationInstanceClass="dms.t2.micro",
        AllocatedStorage=50,
        VpcSecurityGroupIds=["sg-12345"],
        AvailabilityZone="us-east-1a",
        ReplicationSubnetGroupIdentifier="default-subnet-group",
        PreferredMaintenanceWindow="sun:06:00-sun:14:00",
        MultiAZ=False,
        EngineVersion="3.4.6",
        AutoMinorVersionUpgrade=True,
        Tags=[{"Key": "Name", "Value": "Test Instance"}],
        PubliclyAccessible=True,
        NetworkType="IPV4",
    )

    instance = response["ReplicationInstance"]
    assert instance["ReplicationInstanceIdentifier"] == "test-instance"
    assert instance["ReplicationInstanceClass"] == "dms.t2.micro"
    assert instance["AllocatedStorage"] == 50
    assert instance["AvailabilityZone"] == "us-east-1a"
    assert instance["ReplicationInstanceStatus"] == "creating"
    assert instance["MultiAZ"] is False
    assert instance["EngineVersion"] == "3.4.6"
    assert instance["AutoMinorVersionUpgrade"] is True
    assert instance["PubliclyAccessible"] is True
    assert instance["NetworkType"] == "IPV4"

    arn = instance["ReplicationInstanceArn"]
    assert arn.startswith("arn:aws:dms:us-east-1:")
    assert ":rep:test-instance" in arn

    response = client.describe_replication_instances(
        Filters=[{"Name": "replication-instance-id", "Values": ["test-instance"]}]
    )
    assert len(response["ReplicationInstances"]) == 1
    assert (
        response["ReplicationInstances"][0]["ReplicationInstanceIdentifier"]
        == "test-instance"
    )


@mock_aws
def test_describe_replication_instances():
    client = boto3.client("dms", region_name="us-east-1")

    client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-1",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
    )

    client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-2",
        ReplicationInstanceClass="dms.t2.small",
        EngineVersion="3.4.6",
    )

    response = client.describe_replication_instances()
    instances = response["ReplicationInstances"]
    assert len(instances) == 2

    response = client.describe_replication_instances(
        Filters=[{"Name": "replication-instance-class", "Values": ["dms.t2.micro"]}]
    )
    instances = response["ReplicationInstances"]
    assert len(instances) == 1
    assert instances[0]["ReplicationInstanceIdentifier"] == "test-instance-1"

    response = client.describe_replication_instances(
        Filters=[{"Name": "engine-version", "Values": ["3.4.6"]}]
    )
    instances = response["ReplicationInstances"]
    assert len(instances) == 1
    assert instances[0]["ReplicationInstanceIdentifier"] == "test-instance-2"
