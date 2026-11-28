"""Unit tests for docdb-elastic-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

TEST_REGION = "us-east-1"


def create_cluster(client, name="my-cluster", **kwargs):
    params = {
        "clusterName": name,
        "adminUserName": "admin",
        "adminUserPassword": "hunter2000",
        "authType": "PLAIN_TEXT",
        "shardCapacity": 2,
        "shardCount": 2,
    }
    params.update(kwargs)
    return client.create_cluster(**params)["cluster"]


@mock_aws
def test_create_cluster():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    cluster = create_cluster(client, tags={"env": "test"})

    assert cluster["clusterName"] == "my-cluster"
    assert cluster["clusterArn"].startswith(
        "arn:aws:docdb-elastic:us-east-1:123456789012:cluster/"
    )
    assert cluster["clusterEndpoint"].endswith(".us-east-1.docdb-elastic.amazonaws.com")
    assert cluster["adminUserName"] == "admin"
    assert cluster["authType"] == "PLAIN_TEXT"
    assert cluster["status"] == "ACTIVE"
    assert cluster["shardCapacity"] == 2
    assert cluster["shardCount"] == 2
    assert cluster["shardInstanceCount"] == 1
    assert cluster["backupRetentionPeriod"] == 1
    assert cluster["kmsKeyId"] == "AWS_OWNED_KMS_KEY"
    assert "createTime" in cluster
    assert "preferredBackupWindow" in cluster
    assert "preferredMaintenanceWindow" in cluster
    assert len(cluster["shards"]) == 2
    for shard in cluster["shards"]:
        assert shard["status"] == "ACTIVE"
        assert "shardId" in shard
        assert "createTime" in shard

    assert client.list_tags_for_resource(resourceArn=cluster["clusterArn"])["tags"] == {
        "env": "test"
    }


@mock_aws
def test_create_cluster__with_additional_params():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    cluster = create_cluster(
        client,
        shardInstanceCount=3,
        backupRetentionPeriod=7,
        preferredBackupWindow="01:00-02:00",
        preferredMaintenanceWindow="mon:03:00-mon:04:00",
        kmsKeyId="arn:aws:kms:us-east-1:123456789012:key/my-key",
        subnetIds=["subnet-1", "subnet-2"],
        vpcSecurityGroupIds=["sg-1"],
    )
    assert cluster["shardInstanceCount"] == 3
    assert cluster["backupRetentionPeriod"] == 7
    assert cluster["preferredBackupWindow"] == "01:00-02:00"
    assert cluster["preferredMaintenanceWindow"] == "mon:03:00-mon:04:00"
    assert cluster["kmsKeyId"] == "arn:aws:kms:us-east-1:123456789012:key/my-key"
    assert cluster["subnetIds"] == ["subnet-1", "subnet-2"]
    assert cluster["vpcSecurityGroupIds"] == ["sg-1"]


@mock_aws
def test_create_cluster__duplicate_name():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    create_cluster(client)
    with pytest.raises(ClientError) as exc:
        create_cluster(client)
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert exc.value.response["resourceType"] == "cluster"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 409


@mock_aws
@pytest.mark.parametrize(
    "kwargs",
    [
        {"shardCapacity": 3},
        {"shardCount": 0},
        {"shardCount": 33},
        {"adminUserPassword": ""},
    ],
)
def test_create_cluster__invalid_params(kwargs):
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    with pytest.raises(ClientError) as exc:
        create_cluster(client, **kwargs)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400


@mock_aws
def test_get_cluster():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]

    cluster = client.get_cluster(clusterArn=arn)["cluster"]
    assert cluster["clusterArn"] == arn
    assert cluster["clusterName"] == "my-cluster"
    assert cluster["status"] == "ACTIVE"


@mock_aws
def test_get_cluster__unknown():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = "arn:aws:docdb-elastic:us-east-1:123456789012:cluster/unknown"
    with pytest.raises(ClientError) as exc:
        client.get_cluster(clusterArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert exc.value.response["resourceId"] == arn
    assert exc.value.response["resourceType"] == "cluster"
    assert exc.value.response["ResponseMetadata"]["HTTPStatusCode"] == 404


@mock_aws
def test_list_clusters():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    assert client.list_clusters()["clusters"] == []

    arns = [create_cluster(client, name=f"cluster-{i}")["clusterArn"] for i in range(3)]

    clusters = client.list_clusters()["clusters"]
    assert [c["clusterArn"] for c in clusters] == arns
    assert clusters[0] == {
        "clusterArn": arns[0],
        "clusterName": "cluster-0",
        "status": "ACTIVE",
    }

    # Clusters are regional
    other = boto3.client("docdb-elastic", region_name="eu-west-1")
    assert other.list_clusters()["clusters"] == []


@mock_aws
def test_list_clusters__pagination():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    for i in range(3):
        create_cluster(client, name=f"cluster-{i}")

    page = client.list_clusters(maxResults=2)
    assert len(page["clusters"]) == 2
    assert "nextToken" in page

    page = client.list_clusters(maxResults=2, nextToken=page["nextToken"])
    assert [c["clusterName"] for c in page["clusters"]] == ["cluster-2"]
    assert "nextToken" not in page

    paginator = client.get_paginator("list_clusters")
    names = [
        c["clusterName"]
        for page in paginator.paginate(PaginationConfig={"PageSize": 1})
        for c in page["clusters"]
    ]
    assert names == ["cluster-0", "cluster-1", "cluster-2"]


@mock_aws
def test_update_cluster():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]

    cluster = client.update_cluster(
        clusterArn=arn,
        shardCapacity=8,
        shardCount=4,
        shardInstanceCount=2,
        backupRetentionPeriod=14,
        preferredBackupWindow="02:00-03:00",
        preferredMaintenanceWindow="tue:03:00-tue:04:00",
        subnetIds=["subnet-9"],
        vpcSecurityGroupIds=["sg-9"],
        authType="SECRET_ARN",
    )["cluster"]
    assert cluster["shardCapacity"] == 8
    assert cluster["shardCount"] == 4
    assert len(cluster["shards"]) == 4
    assert cluster["shardInstanceCount"] == 2
    assert cluster["backupRetentionPeriod"] == 14
    assert cluster["preferredBackupWindow"] == "02:00-03:00"
    assert cluster["preferredMaintenanceWindow"] == "tue:03:00-tue:04:00"
    assert cluster["subnetIds"] == ["subnet-9"]
    assert cluster["vpcSecurityGroupIds"] == ["sg-9"]
    assert cluster["authType"] == "SECRET_ARN"

    cluster = client.update_cluster(clusterArn=arn, shardCount=1)["cluster"]
    assert len(cluster["shards"]) == 1

    cluster = client.get_cluster(clusterArn=arn)["cluster"]
    assert cluster["shardCapacity"] == 8
    assert cluster["shardCount"] == 1


@mock_aws
def test_update_cluster__invalid_shard_capacity():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]
    with pytest.raises(ClientError) as exc:
        client.update_cluster(clusterArn=arn, shardCapacity=5)
    assert exc.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_delete_cluster():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]

    cluster = client.delete_cluster(clusterArn=arn)["cluster"]
    assert cluster["clusterArn"] == arn
    assert cluster["status"] == "DELETING"

    with pytest.raises(ClientError) as exc:
        client.get_cluster(clusterArn=arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert client.list_clusters()["clusters"] == []


@mock_aws
def test_delete_cluster__unknown():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    with pytest.raises(ClientError) as exc:
        client.delete_cluster(
            clusterArn="arn:aws:docdb-elastic:us-east-1:123456789012:cluster/unknown"
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_stop_and_start_cluster():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]

    cluster = client.stop_cluster(clusterArn=arn)["cluster"]
    assert cluster["status"] == "STOPPED"
    assert client.get_cluster(clusterArn=arn)["cluster"]["status"] == "STOPPED"

    # Stopping an already stopped cluster is a conflict
    with pytest.raises(ClientError) as exc:
        client.stop_cluster(clusterArn=arn)
    assert exc.value.response["Error"]["Code"] == "ConflictException"

    cluster = client.start_cluster(clusterArn=arn)["cluster"]
    assert cluster["status"] == "ACTIVE"

    # Starting an already active cluster is a conflict
    with pytest.raises(ClientError) as exc:
        client.start_cluster(clusterArn=arn)
    assert exc.value.response["Error"]["Code"] == "ConflictException"


@mock_aws
def test_create_cluster_snapshot():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    cluster = create_cluster(
        client, subnetIds=["subnet-1"], vpcSecurityGroupIds=["sg-1"]
    )
    arn = cluster["clusterArn"]

    snapshot = client.create_cluster_snapshot(
        clusterArn=arn, snapshotName="snap-1", tags={"k": "v"}
    )["snapshot"]
    assert snapshot["snapshotName"] == "snap-1"
    assert snapshot["snapshotArn"].startswith(
        "arn:aws:docdb-elastic:us-east-1:123456789012:cluster-snapshot/"
    )
    assert snapshot["clusterArn"] == arn
    assert snapshot["clusterCreationTime"] == cluster["createTime"]
    assert snapshot["adminUserName"] == "admin"
    assert snapshot["kmsKeyId"] == "AWS_OWNED_KMS_KEY"
    assert snapshot["snapshotType"] == "MANUAL"
    assert snapshot["status"] == "ACTIVE"
    assert snapshot["subnetIds"] == ["subnet-1"]
    assert snapshot["vpcSecurityGroupIds"] == ["sg-1"]
    assert "snapshotCreationTime" in snapshot

    assert client.list_tags_for_resource(resourceArn=snapshot["snapshotArn"])[
        "tags"
    ] == {"k": "v"}


@mock_aws
def test_create_cluster_snapshot__errors():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]
    client.create_cluster_snapshot(clusterArn=arn, snapshotName="snap-1")

    with pytest.raises(ClientError) as exc:
        client.create_cluster_snapshot(clusterArn=arn, snapshotName="snap-1")
    assert exc.value.response["Error"]["Code"] == "ConflictException"

    with pytest.raises(ClientError) as exc:
        client.create_cluster_snapshot(
            clusterArn="arn:aws:docdb-elastic:us-east-1:123456789012:cluster/unknown",
            snapshotName="snap-2",
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_cluster_snapshot():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]
    snapshot_arn = client.create_cluster_snapshot(
        clusterArn=arn, snapshotName="snap-1"
    )["snapshot"]["snapshotArn"]

    snapshot = client.get_cluster_snapshot(snapshotArn=snapshot_arn)["snapshot"]
    assert snapshot["snapshotArn"] == snapshot_arn
    assert snapshot["snapshotName"] == "snap-1"

    with pytest.raises(ClientError) as exc:
        client.get_cluster_snapshot(
            snapshotArn="arn:aws:docdb-elastic:us-east-1:123456789012:cluster-snapshot/unknown"
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert exc.value.response["resourceType"] == "cluster-snapshot"


@mock_aws
def test_list_cluster_snapshots():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    assert client.list_cluster_snapshots()["snapshots"] == []

    arn1 = create_cluster(client, name="cluster-1")["clusterArn"]
    arn2 = create_cluster(client, name="cluster-2")["clusterArn"]
    client.create_cluster_snapshot(clusterArn=arn1, snapshotName="snap-1")
    client.create_cluster_snapshot(clusterArn=arn1, snapshotName="snap-2")
    client.create_cluster_snapshot(clusterArn=arn2, snapshotName="snap-3")

    snapshots = client.list_cluster_snapshots()["snapshots"]
    assert [s["snapshotName"] for s in snapshots] == ["snap-1", "snap-2", "snap-3"]
    assert set(snapshots[0]) == {
        "clusterArn",
        "snapshotArn",
        "snapshotCreationTime",
        "snapshotName",
        "status",
    }

    snapshots = client.list_cluster_snapshots(clusterArn=arn2)["snapshots"]
    assert [s["snapshotName"] for s in snapshots] == ["snap-3"]

    snapshots = client.list_cluster_snapshots(snapshotType="MANUAL")["snapshots"]
    assert len(snapshots) == 3
    assert client.list_cluster_snapshots(snapshotType="AUTOMATED")["snapshots"] == []


@mock_aws
def test_copy_cluster_snapshot():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]
    source_arn = client.create_cluster_snapshot(
        clusterArn=arn, snapshotName="snap-1", tags={"k1": "v1"}
    )["snapshot"]["snapshotArn"]

    copied = client.copy_cluster_snapshot(
        snapshotArn=source_arn,
        targetSnapshotName="snap-2",
        copyTags=True,
        tags={"k2": "v2"},
        kmsKeyId="arn:aws:kms:us-east-1:123456789012:key/my-key",
    )["snapshot"]
    assert copied["snapshotName"] == "snap-2"
    assert copied["snapshotArn"] != source_arn
    assert copied["clusterArn"] == arn
    assert copied["kmsKeyId"] == "arn:aws:kms:us-east-1:123456789012:key/my-key"
    assert copied["status"] == "ACTIVE"
    assert client.list_tags_for_resource(resourceArn=copied["snapshotArn"])["tags"] == {
        "k1": "v1",
        "k2": "v2",
    }

    without_tags = client.copy_cluster_snapshot(
        snapshotArn=source_arn, targetSnapshotName="snap-3"
    )["snapshot"]
    assert (
        client.list_tags_for_resource(resourceArn=without_tags["snapshotArn"])["tags"]
        == {}
    )

    assert len(client.list_cluster_snapshots()["snapshots"]) == 3

    with pytest.raises(ClientError) as exc:
        client.copy_cluster_snapshot(
            snapshotArn=source_arn, targetSnapshotName="snap-2"
        )
    assert exc.value.response["Error"]["Code"] == "ConflictException"


@mock_aws
def test_delete_cluster_snapshot():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]
    snapshot_arn = client.create_cluster_snapshot(
        clusterArn=arn, snapshotName="snap-1"
    )["snapshot"]["snapshotArn"]

    snapshot = client.delete_cluster_snapshot(snapshotArn=snapshot_arn)["snapshot"]
    assert snapshot["snapshotArn"] == snapshot_arn
    assert snapshot["status"] == "DELETING"

    with pytest.raises(ClientError) as exc:
        client.get_cluster_snapshot(snapshotArn=snapshot_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    assert client.list_cluster_snapshots()["snapshots"] == []


@mock_aws
def test_restore_cluster_from_snapshot():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client, shardCapacity=4, shardCount=3, subnetIds=["subnet-1"])[
        "clusterArn"
    ]
    snapshot_arn = client.create_cluster_snapshot(
        clusterArn=arn, snapshotName="snap-1"
    )["snapshot"]["snapshotArn"]
    # The snapshot outlives the cluster
    client.delete_cluster(clusterArn=arn)

    restored = client.restore_cluster_from_snapshot(
        snapshotArn=snapshot_arn, clusterName="restored", tags={"k": "v"}
    )["cluster"]
    assert restored["clusterName"] == "restored"
    assert restored["clusterArn"] != arn
    assert restored["adminUserName"] == "admin"
    assert restored["authType"] == "PLAIN_TEXT"
    assert restored["shardCapacity"] == 4
    assert restored["shardCount"] == 3
    assert len(restored["shards"]) == 3
    assert restored["subnetIds"] == ["subnet-1"]
    assert restored["status"] == "ACTIVE"
    assert client.list_tags_for_resource(resourceArn=restored["clusterArn"])[
        "tags"
    ] == {"k": "v"}

    overridden = client.restore_cluster_from_snapshot(
        snapshotArn=snapshot_arn,
        clusterName="restored-2",
        shardCapacity=16,
        shardInstanceCount=2,
        subnetIds=["subnet-2"],
        vpcSecurityGroupIds=["sg-2"],
        kmsKeyId="arn:aws:kms:us-east-1:123456789012:key/my-key",
    )["cluster"]
    assert overridden["shardCapacity"] == 16
    assert overridden["shardInstanceCount"] == 2
    assert overridden["subnetIds"] == ["subnet-2"]
    assert overridden["vpcSecurityGroupIds"] == ["sg-2"]
    assert overridden["kmsKeyId"] == "arn:aws:kms:us-east-1:123456789012:key/my-key"

    assert len(client.list_clusters()["clusters"]) == 2


@mock_aws
def test_tagging():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client, tags={"k1": "v1"})["clusterArn"]

    client.tag_resource(resourceArn=arn, tags={"k2": "v2", "k3": "v3"})
    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {
        "k1": "v1",
        "k2": "v2",
        "k3": "v3",
    }

    client.untag_resource(resourceArn=arn, tagKeys=["k1", "k3", "unknown"])
    assert client.list_tags_for_resource(resourceArn=arn)["tags"] == {"k2": "v2"}

    snapshot_arn = client.create_cluster_snapshot(
        clusterArn=arn, snapshotName="snap-1"
    )["snapshot"]["snapshotArn"]
    client.tag_resource(resourceArn=snapshot_arn, tags={"s": "1"})
    assert client.list_tags_for_resource(resourceArn=snapshot_arn)["tags"] == {"s": "1"}

    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(
            resourceArn="arn:aws:docdb-elastic:us-east-1:123456789012:cluster/unknown"
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_pending_maintenance_actions():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client)["clusterArn"]

    assert (
        client.list_pending_maintenance_actions()["resourcePendingMaintenanceActions"]
        == []
    )

    resp = client.get_pending_maintenance_action(resourceArn=arn)[
        "resourcePendingMaintenanceAction"
    ]
    assert resp == {"resourceArn": arn, "pendingMaintenanceActionDetails": []}

    resp = client.apply_pending_maintenance_action(
        resourceArn=arn, applyAction="ENGINE_UPDATE", optInType="IMMEDIATE"
    )["resourcePendingMaintenanceAction"]
    assert resp == {"resourceArn": arn, "pendingMaintenanceActionDetails": []}

    with pytest.raises(ClientError) as exc:
        client.get_pending_maintenance_action(
            resourceArn="arn:aws:docdb-elastic:us-east-1:123456789012:cluster/unknown"
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_resourcegroupstaggingapi_integration():
    client = boto3.client("docdb-elastic", region_name=TEST_REGION)
    arn = create_cluster(client, tags={"team": "data"})["clusterArn"]

    rtapi = boto3.client("resourcegroupstaggingapi", region_name=TEST_REGION)
    resources = rtapi.get_resources(ResourceTypeFilters=["docdb-elastic"])[
        "ResourceTagMappingList"
    ]
    assert [r["ResourceARN"] for r in resources] == [arn]
    assert resources[0]["Tags"] == [{"Key": "team", "Value": "data"}]
