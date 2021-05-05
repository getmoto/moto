from __future__ import unicode_literals

from botocore.exceptions import ClientError
import boto3
import sure  # noqa
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

    try:
        client.create_replication_task(
            ReplicationTaskIdentifier="test",
            SourceEndpointArn="source-endpoint-arn",
            TargetEndpointArn="target-endpoint-arn",
            ReplicationInstanceArn="replication-instance-arn",
            MigrationType="full-load",
            TableMappings='{"rules":[]}',
        )
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("ResourceAlreadyExistsFault")
        err.response["Error"]["Message"].should.equal(
            "The resource you are attempting to create already exists."
        )
    else:
        raise RuntimeError("Should have raised ResourceAlreadyExistsFault")


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
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn],}]
    )

    tasks["ReplicationTasks"][0]["Status"].should.equal("running")


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

    try:
        client.stop_replication_task(ReplicationTaskArn=task_arn)
    except ClientError as err:
        err.response["Error"]["Code"].should.equal("InvalidResourceStateFault")
        err.response["Error"]["Message"].should.equal("Replication task is not running")


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
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn],}]
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
        Filters=[{"Name": "replication-task-arn", "Values": [task_arn],}]
    )

    tasks["ReplicationTasks"].should.have.length_of(0)
