from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError

from . import mock_rds
from sure import this


test_tags = [
    {"Key": "foo", "Value": "bar",},
    {"Key": "foo1", "Value": "bar1",},
]


@mock_rds
def test_create_db_cluster_snapshot():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
        Tags=test_tags,
    )
    snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap", DBClusterIdentifier="cluster-1"
    ).get("DBClusterSnapshot")
    this(snapshot["DBClusterIdentifier"]).should.equal("cluster-1")


@mock_rds
def test_describe_db_cluster_snapshots_paginated():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
        Tags=test_tags,
    )
    auto_snapshots = client.describe_db_cluster_snapshots(MaxRecords=20).get(
        "DBClusterSnapshots"
    )
    custom_snap_start = len(auto_snapshots)
    for i in range(custom_snap_start, 21):
        client.create_db_cluster_snapshot(
            DBClusterSnapshotIdentifier="cluster-snap-{}".format(i),
            DBClusterIdentifier="cluster-1",
        )

    resp = client.describe_db_cluster_snapshots(MaxRecords=20)
    snaps = resp.get("DBClusterSnapshots")
    snaps.should.have.length_of(20)
    snaps[custom_snap_start]["DBClusterSnapshotIdentifier"].should.equal(
        "cluster-snap-{}".format(custom_snap_start)
    )

    resp2 = client.describe_db_cluster_snapshots(Marker=resp["Marker"])
    resp2["DBClusterSnapshots"].should.have.length_of(1)
    resp2["DBClusterSnapshots"][0]["DBClusterSnapshotIdentifier"].should.equal(
        "cluster-snap-20"
    )

    resp3 = client.describe_db_cluster_snapshots()
    resp3["DBClusterSnapshots"].should.have.length_of(21)


@mock_rds
def test_delete_db_cluster_snapshot():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
    )
    client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap", DBClusterIdentifier="cluster-1"
    )
    snapshots = client.describe_db_cluster_snapshots(
        DBClusterIdentifier="cluster-1", SnapshotType="manual"
    ).get("DBClusterSnapshots")
    snapshots.should.have.length_of(1)
    snapshot = client.delete_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap"
    ).get("DBClusterSnapshot")
    snapshot["DBClusterSnapshotIdentifier"].should.equal("cluster-snap")
    snapshots = client.describe_db_cluster_snapshots(
        DBClusterIdentifier="cluster-1", SnapshotType="manual"
    ).get("DBClusterSnapshots")
    snapshots.should.have.length_of(0)


@mock_rds
def test_delete_non_existent_db_cluster_snapshot_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.delete_db_cluster_snapshot.when.called_with(
        DBClusterSnapshotIdentifier="non-existent"
    ).should.throw(ClientError, "not found")
