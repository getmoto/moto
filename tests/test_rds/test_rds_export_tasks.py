import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_rds
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


def _prepare_db_snapshot(client, snapshot_name="snapshot-1"):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    resp = client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier=snapshot_name
    )
    return resp["DBSnapshot"]["DBSnapshotArn"]


def _prepare_db_cluster_snapshot(client, snapshot_name="cluster-snapshot-1"):
    db_cluster_identifier = "db-cluster-primary-1"
    client.create_db_cluster(
        AvailabilityZones=[
            "us-west-2",
        ],
        BackupRetentionPeriod=1,
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterParameterGroupName="db-cluster-primary-1-group",
        DatabaseName="staging-postgres",
        Engine="postgres",
        EngineVersion="5.6.10a",
        MasterUserPassword="hunterxhunder",
        MasterUsername="root",
        Port=3306,
        StorageEncrypted=True,
    )
    resp = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier=snapshot_name,
        DBClusterIdentifier=db_cluster_identifier,
    )
    return resp["DBClusterSnapshot"]["DBClusterSnapshotArn"]


@mock_rds
def test_start_export_task_fails_unknown_snapshot():
    client = boto3.client("rds", region_name="us-west-2")

    with pytest.raises(ClientError) as ex:
        client.start_export_task(
            ExportTaskIdentifier="export-snapshot-1",
            SourceArn=f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:snapshot:snapshot-1",
            S3BucketName="export-bucket",
            IamRoleArn="",
            KmsKeyId="",
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("DBSnapshotNotFound")
    err["Message"].should.equal("DBSnapshot snapshot-1 not found.")


@mock_rds
def test_start_export_task_db():
    client = boto3.client("rds", region_name="us-west-2")
    source_arn = _prepare_db_snapshot(client)

    export = client.start_export_task(
        ExportTaskIdentifier="export-snapshot-1",
        SourceArn=source_arn,
        S3BucketName="export-bucket",
        S3Prefix="snaps/",
        IamRoleArn="arn:aws:iam:::role/export-role",
        KmsKeyId="arn:aws:kms:::key/0ea3fef3-80a7-4778-9d8c-1c0c6EXAMPLE",
        ExportOnly=["schema.table"],
    )

    export["ExportTaskIdentifier"].should.equal("export-snapshot-1")
    export["SourceArn"].should.equal(source_arn)
    export["S3Bucket"].should.equal("export-bucket")
    export["S3Prefix"].should.equal("snaps/")
    export["IamRoleArn"].should.equal("arn:aws:iam:::role/export-role")
    export["KmsKeyId"].should.equal(
        "arn:aws:kms:::key/0ea3fef3-80a7-4778-9d8c-1c0c6EXAMPLE"
    )
    export["ExportOnly"].should.equal(["schema.table"])
    export["SourceType"].should.equal("SNAPSHOT")


@mock_rds
def test_start_export_task_db_cluster():
    client = boto3.client("rds", region_name="us-west-2")
    source_arn = _prepare_db_cluster_snapshot(client)

    export = client.start_export_task(
        ExportTaskIdentifier="export-snapshot-1",
        SourceArn=source_arn,
        S3BucketName="export-bucket",
        S3Prefix="snaps/",
        IamRoleArn="arn:aws:iam:::role/export-role",
        KmsKeyId="arn:aws:kms:::key/0ea3fef3-80a7-4778-9d8c-1c0c6EXAMPLE",
        ExportOnly=["schema.table"],
    )

    export["ExportTaskIdentifier"].should.equal("export-snapshot-1")
    export["SourceArn"].should.equal(source_arn)
    export["S3Bucket"].should.equal("export-bucket")
    export["S3Prefix"].should.equal("snaps/")
    export["IamRoleArn"].should.equal("arn:aws:iam:::role/export-role")
    export["KmsKeyId"].should.equal(
        "arn:aws:kms:::key/0ea3fef3-80a7-4778-9d8c-1c0c6EXAMPLE"
    )
    export["ExportOnly"].should.equal(["schema.table"])
    export["SourceType"].should.equal("CLUSTER")


@mock_rds
def test_start_export_task_fail_already_exists():
    client = boto3.client("rds", region_name="us-west-2")
    source_arn = _prepare_db_snapshot(client)

    client.start_export_task(
        ExportTaskIdentifier="export-snapshot-1",
        SourceArn=source_arn,
        S3BucketName="export-bucket",
        IamRoleArn="",
        KmsKeyId="",
    )
    with pytest.raises(ClientError) as ex:
        client.start_export_task(
            ExportTaskIdentifier="export-snapshot-1",
            SourceArn=source_arn,
            S3BucketName="export-bucket",
            IamRoleArn="",
            KmsKeyId="",
        )

    err = ex.value.response["Error"]
    err["Code"].should.equal("ExportTaskAlreadyExistsFault")
    err["Message"].should.equal(
        "Cannot start export task because a task with the identifier export-snapshot-1 already exists."
    )


@mock_rds
def test_cancel_export_task_fails_unknown_task():
    client = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.cancel_export_task(ExportTaskIdentifier="export-snapshot-1")

    err = ex.value.response["Error"]
    err["Code"].should.equal("ExportTaskNotFoundFault")
    err["Message"].should.equal(
        "Cannot cancel export task because a task with the identifier export-snapshot-1 is not exist."
    )


@mock_rds
def test_cancel_export_task():
    client = boto3.client("rds", region_name="us-west-2")
    source_arn = _prepare_db_snapshot(client)

    client.start_export_task(
        ExportTaskIdentifier="export-snapshot-1",
        SourceArn=source_arn,
        S3BucketName="export-bucket",
        IamRoleArn="",
        KmsKeyId="",
    )

    export = client.cancel_export_task(ExportTaskIdentifier="export-snapshot-1")

    export["ExportTaskIdentifier"].should.equal("export-snapshot-1")
    export["Status"].should.equal("canceled")


@mock_rds
def test_describe_export_tasks():
    client = boto3.client("rds", region_name="us-west-2")
    source_arn = _prepare_db_snapshot(client)
    client.start_export_task(
        ExportTaskIdentifier="export-snapshot-1",
        SourceArn=source_arn,
        S3BucketName="export-bucket",
        IamRoleArn="",
        KmsKeyId="",
    )

    exports = client.describe_export_tasks().get("ExportTasks")

    exports.should.have.length_of(1)
    exports[0]["ExportTaskIdentifier"].should.equal("export-snapshot-1")


@mock_rds
def test_describe_export_tasks_fails_unknown_task():
    client = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.describe_export_tasks(ExportTaskIdentifier="export-snapshot-1")

    err = ex.value.response["Error"]
    err["Code"].should.equal("ExportTaskNotFoundFault")
    err["Message"].should.equal(
        "Cannot cancel export task because a task with the identifier export-snapshot-1 is not exist."
    )
