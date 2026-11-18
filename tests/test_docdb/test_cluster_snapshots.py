import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


def _create_cluster(client, identifier="cluster-id"):
    return client.create_db_cluster(
        DBClusterIdentifier=identifier,
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Tags=[{"Key": "k1", "Value": "v1"}],
    )["DBCluster"]


@mock_aws
def test_create_db_cluster_snapshot():
    client = boto3.client("docdb", region_name="us-east-1")
    _create_cluster(client)

    snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="snapshot-1",
        DBClusterIdentifier="cluster-id",
        Tags=[{"Key": "k2", "Value": "v2"}],
    )["DBClusterSnapshot"]
    assert snapshot["DBClusterSnapshotIdentifier"] == "snapshot-1"
    assert snapshot["DBClusterIdentifier"] == "cluster-id"
    assert snapshot["Engine"] == "docdb"
    assert snapshot["EngineVersion"] == "5.0.0"
    assert snapshot["Port"] == 27017
    assert snapshot["MasterUsername"] == "root"
    assert snapshot["SnapshotType"] == "manual"
    assert snapshot["Status"] == "available"
    assert "DBClusterSnapshotArn" in snapshot

    tags = client.list_tags_for_resource(ResourceName=snapshot["DBClusterSnapshotArn"])[
        "TagList"
    ]
    assert tags == [{"Key": "k2", "Value": "v2"}]


@mock_aws
def test_describe_db_cluster_snapshots():
    client = boto3.client("docdb", region_name="us-east-1")
    _create_cluster(client)
    _create_cluster(client, identifier="cluster-id-2")
    client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="snapshot-1", DBClusterIdentifier="cluster-id"
    )
    client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="snapshot-2", DBClusterIdentifier="cluster-id-2"
    )

    snapshots = client.describe_db_cluster_snapshots(SnapshotType="manual")[
        "DBClusterSnapshots"
    ]
    assert len(snapshots) == 2

    snapshots = client.describe_db_cluster_snapshots(
        DBClusterIdentifier="cluster-id-2", SnapshotType="manual"
    )["DBClusterSnapshots"]
    assert [s["DBClusterSnapshotIdentifier"] for s in snapshots] == ["snapshot-2"]

    # Automated snapshots are created alongside the cluster
    snapshots = client.describe_db_cluster_snapshots(
        DBClusterIdentifier="cluster-id-2", SnapshotType="automated"
    )["DBClusterSnapshots"]
    assert len(snapshots) == 1
    assert snapshots[0]["DBClusterSnapshotIdentifier"].startswith("rds:cluster-id-2")

    snapshots = client.describe_db_cluster_snapshots(
        DBClusterSnapshotIdentifier="snapshot-1"
    )["DBClusterSnapshots"]
    assert [s["DBClusterSnapshotIdentifier"] for s in snapshots] == ["snapshot-1"]


@mock_aws
def test_copy_db_cluster_snapshot():
    client = boto3.client("docdb", region_name="us-east-1")
    _create_cluster(client)
    client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="snapshot-1", DBClusterIdentifier="cluster-id"
    )
    copied = client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier="snapshot-1",
        TargetDBClusterSnapshotIdentifier="snapshot-2",
    )["DBClusterSnapshot"]
    assert copied["DBClusterSnapshotIdentifier"] == "snapshot-2"
    assert copied["Engine"] == "docdb"

    snapshots = client.describe_db_cluster_snapshots(SnapshotType="manual")[
        "DBClusterSnapshots"
    ]
    assert len(snapshots) == 2


@mock_aws
def test_restore_db_cluster_from_snapshot():
    client = boto3.client("docdb", region_name="us-east-1")
    _create_cluster(client)
    client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="snapshot-1", DBClusterIdentifier="cluster-id"
    )
    restored = client.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="restored-cluster",
        SnapshotIdentifier="snapshot-1",
        Engine="docdb",
    )["DBCluster"]
    assert restored["DBClusterIdentifier"] == "restored-cluster"
    assert restored["Engine"] == "docdb"
    assert restored["EngineVersion"] == "5.0.0"
    assert restored["Port"] == 27017

    clusters = client.describe_db_clusters()["DBClusters"]
    assert len(clusters) == 2


@mock_aws
def test_delete_db_cluster_snapshot():
    client = boto3.client("docdb", region_name="us-east-1")
    _create_cluster(client)
    client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="snapshot-1", DBClusterIdentifier="cluster-id"
    )
    client.delete_db_cluster_snapshot(DBClusterSnapshotIdentifier="snapshot-1")

    with pytest.raises(ClientError) as exc:
        client.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier="snapshot-1")
    err = exc.value.response["Error"]
    assert err["Code"] == "DBClusterSnapshotNotFoundFault"
