from botocore.exceptions import ClientError
import boto3
import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_dms


@mock_dms
def test_create_and_get_replication_task():
    client = boto3.client("dms", region_name="us-east-1")

    client.create_replication_task(
        ReplicationTaskIdentifier="test",
        SourceEndpointArn="source-endpoint-arn",
        TargetEndpointArn="target-endpoint-arn",
        ReplicationInstanceArn="replication-instance-arn",
        MigrationType="full-load",
        TableMappings='{"rules":[]}',
    )

    tasks = client.describe_replication_tasks(
        Filters=[{"Name": "replication-task-id", "Values": ["test"]}]
    )

    tasks["ReplicationTasks"].should.have.length_of(1)
    task = tasks["ReplicationTasks"][0]
    task["ReplicationTaskIdentifier"].should.equal("test")
    task["SourceEndpointArn"].should.equal("source-endpoint-arn")
    task["TargetEndpointArn"].should.equal("target-endpoint-arn")
    task["ReplicationInstanceArn"].should.equal("replication-instance-arn")
    task["MigrationType"].should.equal("full-load")
    task["Status"].should.equal("creating")


@mock_dms
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

    ex.value.operation_name.should.equal("CreateReplicationTask")
    ex.value.response["Error"]["Code"].should.equal("ResourceAlreadyExistsFault")
    ex.value.response["Error"]["Message"].should.equal(
        "The resource you are attempting to create already exists."
    )


@mock_dms
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

    tasks["ReplicationTasks"][0]["Status"].should.equal("running")


@mock_dms
def test_start_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.start_replication_task(
            ReplicationTaskArn="does-not-exist",
            StartReplicationTaskType="start-replication",
        )

    ex.value.operation_name.should.equal("StartReplicationTask")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Replication task could not be found."
    )


@mock_dms
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

    ex.value.operation_name.should.equal("StopReplicationTask")
    ex.value.response["Error"]["Code"].should.equal("InvalidResourceStateFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Replication task is not running"
    )


@mock_dms
def test_stop_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.stop_replication_task(ReplicationTaskArn="does-not-exist")

    ex.value.operation_name.should.equal("StopReplicationTask")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Replication task could not be found."
    )


@mock_dms
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

    tasks["ReplicationTasks"][0]["Status"].should.equal("stopped")


@mock_dms
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

    tasks["ReplicationTasks"].should.have.length_of(0)


@mock_dms
def test_delete_replication_task_throws_resource_not_found_error():
    client = boto3.client("dms", region_name="us-east-1")

    with pytest.raises(ClientError) as ex:
        client.delete_replication_task(ReplicationTaskArn="does-not-exist")

    ex.value.operation_name.should.equal("DeleteReplicationTask")
    ex.value.response["Error"]["Code"].should.equal("ResourceNotFoundFault")
    ex.value.response["Error"]["Message"].should.equal(
        "Replication task could not be found."
    )
