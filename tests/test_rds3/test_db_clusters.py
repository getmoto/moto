from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError

from . import mock_rds, mock_ec2
from sure import this


# TODO: Add tests for vpc, subnet, and param group parameters
# TODO: Test that calling describe on cluster members returns the cluster DatabaseName as the DBName

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
def test_create_db_cluster():
    client = boto3.client("rds", region_name="us-west-2")
    cluster = client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
        Tags=test_tags,
    ).get("DBCluster")
    this(cluster["DBClusterIdentifier"]).should.equal("cluster-1")
    tag_list = client.list_tags_for_resource(ResourceName=cluster["DBClusterArn"]).get(
        "TagList"
    )
    this(tag_list).should.equal(test_tags)


@mock_rds
def test_modify_db_cluster():
    client = boto3.client("rds", region_name="us-west-2")
    cluster_id = "cluster-1"
    cluster = client.create_db_cluster(
        DBClusterIdentifier=cluster_id,
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
        BackupRetentionPeriod=7,
    ).get("DBCluster")
    new_backup_retention = cluster["BackupRetentionPeriod"] + 7
    new_cluster_id = cluster_id + "-new"
    cluster = client.modify_db_cluster(
        DBClusterIdentifier=cluster_id,
        NewDBClusterIdentifier=new_cluster_id,
        BackupRetentionPeriod=new_backup_retention,
    ).get("DBCluster")
    cluster["DBClusterIdentifier"].should.equal(new_cluster_id)
    cluster["BackupRetentionPeriod"].should.equal(new_backup_retention)
    cluster = client.describe_db_clusters(DBClusterIdentifier=new_cluster_id).get(
        "DBClusters"
    )[0]
    cluster["DBClusterIdentifier"].should.equal(new_cluster_id)
    cluster["BackupRetentionPeriod"].should.equal(new_backup_retention)


@mock_rds
def test_create_db_cluster_with_parameters():
    client = boto3.client("rds", region_name="us-west-2")
    parameters = {
        "AvailabilityZones": ["us-west-2a", "us-west-2b"],
        "BackupRetentionPeriod": 15,
        "DatabaseName": "custom",
        "DBClusterIdentifier": "test-cluster",
        "DBClusterParameterGroupName": "default.aurora-postgresql9.6",
        "VpcSecurityGroupIds": ["string",],
        # 'DBSubnetGroupName': 'string',
        "Engine": "aurora-postgresql",
        "EngineVersion": "9.6.3",
        "Port": 123,
        "MasterUsername": "root",
        "MasterUserPassword": "password",
        "OptionGroupName": "string",
        "PreferredBackupWindow": "string",
        "PreferredMaintenanceWindow": "string",
        "StorageEncrypted": True,
        "KmsKeyId": "string",
        "EnableIAMDatabaseAuthentication": True,
    }
    cluster = client.create_db_cluster(**parameters).get("DBCluster")
    for attr in parameters:
        if attr in cluster:
            cluster[attr].should.equal(parameters[attr])


@mock_rds
def test_create_db_cluster_with_invalid_availability_zone_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster.when.called_with(
        DBClusterIdentifier="test-cluster",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="password",
        AvailabilityZones=["bad-zone"],
    ).should.throw(ClientError, "zone '[bad-zone]' is unavailable")
    client.create_db_cluster.when.called_with(
        DBClusterIdentifier="test-cluster",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="password",
        AvailabilityZones=["bad-zone1", "bad-zone2"],
    ).should.throw(ClientError, "zones '[bad-zone1, bad-zone2]' are unavailable")


@mock_rds
def test_create_db_cluster_with_invalid_engine_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster.when.called_with(
        DBClusterIdentifier="cluster-1",
        Engine="bad-engine-value",
        MasterUsername="root",
        MasterUserPassword="password",
    ).should.throw(ClientError, "Invalid DB engine")


@mock_rds
def test_create_db_cluster_with_invalid_engine_version_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster.when.called_with(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
        EngineVersion="1.0",
        MasterUsername="root",
        MasterUserPassword="password",
    ).should.throw(ClientError, "Cannot find version 1.0 for aurora-postgresql")


@mock_rds
def test_add_remove_db_instance_from_db_cluster():
    client = boto3.client("rds", region_name="us-west-2")
    cluster = client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
    ).get("DBCluster")
    cluster["DBClusterMembers"].should.have.length_of(0)
    client.create_db_instance(
        DBInstanceIdentifier="test-instance",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    cluster["DBClusterMembers"].should.have.length_of(1)
    client.delete_db_instance(DBInstanceIdentifier="test-instance")
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    cluster["DBClusterMembers"].should.have.length_of(0)


@mock_rds
def test_db_cluster_writer_promotion():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
    )
    for i in range(3):
        client.create_db_instance(
            DBInstanceIdentifier="test-instance-{}".format(i),
            DBInstanceClass="db.m1.small",
            Engine="aurora-postgresql",
            DBClusterIdentifier="cluster-1",
            PromotionTier=15 - i,
        )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    cluster["DBClusterMembers"].should.have.length_of(3)
    writer = next(
        i["DBInstanceIdentifier"]
        for i in cluster["DBClusterMembers"]
        if i["IsClusterWriter"]
    )
    writer.should.equal("test-instance-0")
    client.delete_db_instance(DBInstanceIdentifier="test-instance-0")
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    cluster["DBClusterMembers"].should.have.length_of(2)
    writer = next(
        i["DBInstanceIdentifier"]
        for i in cluster["DBClusterMembers"]
        if i["IsClusterWriter"]
    )
    writer.should.equal("test-instance-2")


@mock_ec2
@mock_rds
def test_db_cluster_multi_az():
    ec2 = boto3.client("ec2", region_name="us-west-2")
    resp = ec2.describe_availability_zones()
    zones = [z["ZoneName"] for z in resp["AvailabilityZones"]]
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
    )
    client.create_db_instance(
        DBInstanceIdentifier="test-zone-a",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
        AvailabilityZone=zones[0],
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    cluster["MultiAZ"].should.equal(False)
    client.create_db_instance(
        DBInstanceIdentifier="test-zone-b",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
        AvailabilityZone=zones[1],
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    cluster["MultiAZ"].should.equal(True)


@mock_rds
def test_describe_db_clusters_paginated():
    client = boto3.client("rds", region_name="us-west-2")
    for i in range(21):
        client.create_db_cluster(
            DBClusterIdentifier="cluster-{}".format(i),
            DatabaseName="db_name",
            Engine="aurora-postgresql",
            MasterUsername="root",
            MasterUserPassword="password",
        )

    resp = client.describe_db_clusters(MaxRecords=20)
    resp["DBClusters"].should.have.length_of(20)
    resp["DBClusters"][0]["DBClusterIdentifier"].should.equal("cluster-0")

    resp2 = client.describe_db_clusters(Marker=resp["Marker"])
    resp2["DBClusters"].should.have.length_of(1)
    resp2["DBClusters"][0]["DBClusterIdentifier"].should.equal("cluster-20")

    resp3 = client.describe_db_clusters()
    resp3["DBClusters"].should.have.length_of(21)


@mock_rds
def test_describe_db_clusters():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    cluster["DBClusterIdentifier"].should.equal("cluster-1")
    cluster["AllocatedStorage"].should.equal(1)
    cluster["BackupRetentionPeriod"].should.equal(1)
    # TODO: check with both supplying an instance id and just a raw dump of all clusters


@mock_rds
def test_delete_db_cluster():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
    )
    cluster = client.delete_db_cluster(DBClusterIdentifier="cluster-1").get("DBCluster")
    cluster["DBClusterIdentifier"].should.equal("cluster-1")
    # TODO: skipfinalsnapshot stuff


@mock_rds
def test_delete_non_existent_db_cluster_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.delete_db_cluster.when.called_with(
        DBClusterIdentifier="non-existent"
    ).should.throw(ClientError, "not found")


@mock_rds
def test_delete_db_cluster_with_active_members_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
    )
    client.create_db_instance(
        DBInstanceIdentifier="test-instance",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
    )
    client.delete_db_cluster.when.called_with(
        DBClusterIdentifier="cluster-1"
    ).should.throw(ClientError, "Cluster cannot be deleted")


@mock_rds
def test_restore_db_cluster_from_snapshot():
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
    cluster = client.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="cluster-from-snapshot",
        SnapshotIdentifier="cluster-snap",
        Engine="aurora-postgresql",
    ).get("DBCluster")
    cluster["DatabaseName"].should.equal("db_name")


@mock_rds
def test_restore_db_cluster_from_snapshot_with_parameters():
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
    cluster = client.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="cluster-from-snapshot",
        SnapshotIdentifier="cluster-snap",
        Engine="aurora-postgresql",
        DatabaseName="new_db_name",
        Port=4321,
        Tags=test_tags,
    ).get("DBCluster")
    cluster["DatabaseName"].should.equal("new_db_name")
    cluster["Port"].should.equal(4321)
    tags = client.list_tags_for_resource(ResourceName=cluster["DBClusterArn"]).get(
        "TagList"
    )
    tags.should.equal(test_tags)


@mock_rds
def test_modify_db_cluster_updates_cluster_instances():
    cluster_only_attributes = {
        "create": {
            "BackupRetentionPeriod": 7,
            "CharacterSetName": "char-set-1",
            "EngineVersion": "10.4",
            "PreferredBackupWindow": "13:30-14:00",
            "StorageEncrypted": True,
        },
        "modify": {
            "BackupRetentionPeriod": 15,
            "EngineVersion": "10.5",
            "PreferredBackupWindow": "14:30-15:00",
        },
    }
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        **cluster_only_attributes["create"]
    )
    fmt_instance_id = "test-instance-{id}"
    for i in range(3):
        instance = client.create_db_instance(
            DBInstanceIdentifier=fmt_instance_id.format(id=i),
            DBInstanceClass="db.m1.small",
            Engine="aurora-postgresql",
            DBClusterIdentifier="cluster-1",
            PromotionTier=15 - i,
        )["DBInstance"]
        for attr, value in cluster_only_attributes["create"].items():
            instance[attr].should.equal(value)
        instance["AllocatedStorage"].should.equal(1)
        instance["StorageType"].should.equal("aurora")

    client.modify_db_cluster(
        DBClusterIdentifier="cluster-1", **cluster_only_attributes["modify"]
    )
    for i in range(3):
        instance = client.describe_db_instances(
            DBInstanceIdentifier=fmt_instance_id.format(id=i),
        )["DBInstances"][0]
        for attr, value in cluster_only_attributes["modify"].items():
            instance[attr].should.equal(value)


@mock_rds
def test_restore_db_instance_to_point_in_time():
    client = boto3.client("rds", region_name="us-west-2")
    details_source = client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
        CopyTagsToSnapshot=True,
    ).get("DBCluster")
    details_target = client.restore_db_cluster_to_point_in_time(
        SourceDBClusterIdentifier="cluster-1",
        DBClusterIdentifier="pit-id",
        UseLatestRestorableTime=True,
    )["DBCluster"]
    details_target["CopyTagsToSnapshot"].should.equal(
        details_source["CopyTagsToSnapshot"]
    )
    details_target["Port"].should.equal(details_source["Port"])
