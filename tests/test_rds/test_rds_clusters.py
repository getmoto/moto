import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_rds
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_rds
def test_describe_db_cluster_initial():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.describe_db_clusters()
    resp.should.have.key("DBClusters").should.have.length_of(0)


@mock_rds
def test_describe_db_cluster_fails_for_non_existent_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.describe_db_clusters()
    resp.should.have.key("DBClusters").should.have.length_of(0)
    with pytest.raises(ClientError) as ex:
        client.describe_db_clusters(DBClusterIdentifier="cluster-id")
    err = ex.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")
    err["Message"].should.equal("DBCluster cluster-id not found.")


@mock_rds
def test_create_db_cluster_needs_master_username():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="aurora")
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The parameter MasterUsername must be provided and must not be blank."
    )


@mock_rds
def test_create_db_cluster_needs_master_user_password():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id", Engine="aurora", MasterUsername="root"
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The parameter MasterUserPassword must be provided and must not be blank."
    )


@mock_rds
def test_create_db_cluster_needs_long_master_user_password():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id",
            Engine="aurora",
            MasterUsername="root",
            MasterUserPassword="hunter2",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The parameter MasterUserPassword is not a valid password because it is shorter than 8 characters."
    )


@mock_rds
def test_modify_db_cluster_needs_long_master_user_password():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster(
            DBClusterIdentifier="cluster-id",
            MasterUserPassword="hunter2",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The parameter MasterUserPassword is not a valid password because it is shorter than 8 characters."
    )


@mock_rds
def test_modify_db_cluster_new_cluster_identifier():
    client = boto3.client("rds", region_name="eu-north-1")
    old_id = "cluster-id"
    new_id = "new-cluster-id"

    client.create_db_cluster(
        DBClusterIdentifier=old_id,
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    resp = client.modify_db_cluster(
        DBClusterIdentifier=old_id,
        NewDBClusterIdentifier=new_id,
        MasterUserPassword="hunter21",
    )

    resp["DBCluster"].should.have.key("DBClusterIdentifier").equal(new_id)

    clusters = [
        cluster["DBClusterIdentifier"]
        for cluster in client.describe_db_clusters()["DBClusters"]
    ]

    assert old_id not in clusters


@mock_rds
def test_create_db_cluster__verify_default_properties():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    resp.should.have.key("DBCluster")

    cluster = resp["DBCluster"]

    cluster.shouldnt.have.key(
        "DatabaseName"
    )  # This was not supplied, so should not be returned

    cluster.should.have.key("AvailabilityZones")
    set(cluster["AvailabilityZones"]).should.equal(
        {"eu-north-1a", "eu-north-1b", "eu-north-1c"}
    )
    cluster.should.have.key("BackupRetentionPeriod").equal(1)
    cluster.should.have.key("DBClusterIdentifier").equal("cluster-id")
    cluster.should.have.key("DBClusterParameterGroup").equal("default.aurora8.0")
    cluster.should.have.key("DBSubnetGroup").equal("default")
    cluster.should.have.key("Status").equal("creating")
    cluster.should.have.key("Endpoint").match(
        "cluster-id.cluster-[a-z0-9]{12}.eu-north-1.rds.amazonaws.com"
    )
    endpoint = cluster["Endpoint"]
    expected_readonly = endpoint.replace(
        "cluster-id.cluster-", "cluster-id.cluster-ro-"
    )
    cluster.should.have.key("ReaderEndpoint").equal(expected_readonly)
    cluster.should.have.key("MultiAZ").equal(False)
    cluster.should.have.key("Engine").equal("aurora")
    cluster.should.have.key("EngineVersion").equal("5.6.mysql_aurora.1.22.5")
    cluster.should.have.key("Port").equal(3306)
    cluster.should.have.key("MasterUsername").equal("root")
    cluster.should.have.key("PreferredBackupWindow").equal("01:37-02:07")
    cluster.should.have.key("PreferredMaintenanceWindow").equal("wed:02:40-wed:03:10")
    cluster.should.have.key("ReadReplicaIdentifiers").equal([])
    cluster.should.have.key("DBClusterMembers").equal([])
    cluster.should.have.key("VpcSecurityGroups")
    cluster.should.have.key("HostedZoneId")
    cluster.should.have.key("StorageEncrypted").equal(False)
    cluster.should.have.key("DbClusterResourceId").match(r"cluster-[A-Z0-9]{26}")
    cluster.should.have.key("DBClusterArn").equal(
        f"arn:aws:rds:eu-north-1:{ACCOUNT_ID}:cluster:cluster-id"
    )
    cluster.should.have.key("AssociatedRoles").equal([])
    cluster.should.have.key("IAMDatabaseAuthenticationEnabled").equal(False)
    cluster.should.have.key("EngineMode").equal("provisioned")
    cluster.should.have.key("DeletionProtection").equal(False)
    cluster.should.have.key("HttpEndpointEnabled").equal(False)
    cluster.should.have.key("CopyTagsToSnapshot").equal(False)
    cluster.should.have.key("CrossAccountClone").equal(False)
    cluster.should.have.key("DeletionProtection").equal(False)
    cluster.should.have.key("DomainMemberships").equal([])
    cluster.should.have.key("TagList").equal([])
    cluster.should.have.key("ClusterCreateTime")
    cluster.should.have.key(
        "EarliestRestorableTime"
    ).should.be.greater_than_or_equal_to(cluster["ClusterCreateTime"])


@mock_rds
def test_create_db_cluster_with_database_name():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        DatabaseName="users",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    cluster = resp["DBCluster"]
    cluster.should.have.key("DatabaseName").equal("users")
    cluster.should.have.key("DBClusterIdentifier").equal("cluster-id")
    cluster.should.have.key("DBClusterParameterGroup").equal("default.aurora8.0")


@mock_rds
def test_create_db_cluster_additional_parameters():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.create_db_cluster(
        AvailabilityZones=["eu-north-1b"],
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        EngineVersion="8.0.mysql_aurora.3.01.0",
        EngineMode="serverless",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        Port=1234,
        DeletionProtection=True,
        EnableCloudwatchLogsExports=["audit"],
        KmsKeyId="some:kms:arn",
        NetworkType="IPV4",
        DBSubnetGroupName="subnetgroupname",
        ScalingConfiguration={
            "MinCapacity": 5,
            "AutoPause": True,
        },
    )

    cluster = resp["DBCluster"]

    cluster.should.have.key("AvailabilityZones").equal(["eu-north-1b"])
    cluster.should.have.key("Engine").equal("aurora")
    cluster.should.have.key("EngineVersion").equal("8.0.mysql_aurora.3.01.0")
    cluster.should.have.key("EngineMode").equal("serverless")
    cluster.should.have.key("Port").equal(1234)
    cluster.should.have.key("DeletionProtection").equal(True)
    cluster.should.have.key("EnabledCloudwatchLogsExports").equals(["audit"])
    assert cluster["KmsKeyId"] == "some:kms:arn"
    assert cluster["NetworkType"] == "IPV4"
    assert cluster["DBSubnetGroup"] == "subnetgroupname"
    assert cluster["ScalingConfigurationInfo"] == {"MinCapacity": 5, "AutoPause": True}


@mock_rds
def test_describe_db_cluster_after_creation():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id1",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    cluster_arn = client.create_db_cluster(
        DBClusterIdentifier="cluster-id2",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )["DBCluster"]["DBClusterArn"]

    client.describe_db_clusters()["DBClusters"].should.have.length_of(2)

    client.describe_db_clusters(DBClusterIdentifier="cluster-id2")[
        "DBClusters"
    ].should.have.length_of(1)

    client.describe_db_clusters(DBClusterIdentifier=cluster_arn)[
        "DBClusters"
    ].should.have.length_of(1)


@mock_rds
def test_delete_db_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    client.delete_db_cluster(DBClusterIdentifier="cluster-id")

    client.describe_db_clusters()["DBClusters"].should.have.length_of(0)


@mock_rds
def test_delete_db_cluster_do_snapshot():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    client.delete_db_cluster(
        DBClusterIdentifier="cluster-id", FinalDBSnapshotIdentifier="final-snapshot"
    )
    client.describe_db_clusters()["DBClusters"].should.have.length_of(0)
    snapshot = client.describe_db_cluster_snapshots()["DBClusterSnapshots"][0]
    assert snapshot["DBClusterIdentifier"] == "cluster-id"
    assert snapshot["DBClusterSnapshotIdentifier"] == "final-snapshot"
    assert snapshot["SnapshotType"] == "automated"


@mock_rds
def test_delete_db_cluster_that_is_protected():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        DeletionProtection=True,
    )

    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier="cluster-id")
    err = exc.value.response["Error"]
    err["Message"].should.equal("Can't delete Cluster with protection enabled")


@mock_rds
def test_delete_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.delete_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")
    err["Message"].should.equal("DBCluster cluster-unknown not found.")


@mock_rds
def test_start_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.start_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")
    err["Message"].should.equal("DBCluster cluster-unknown not found.")


@mock_rds
def test_start_db_cluster_after_stopping():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    client.stop_db_cluster(DBClusterIdentifier="cluster-id")

    client.start_db_cluster(DBClusterIdentifier="cluster-id")
    cluster = client.describe_db_clusters()["DBClusters"][0]
    cluster["Status"].should.equal("available")


@mock_rds
def test_start_db_cluster_without_stopping():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    with pytest.raises(ClientError) as ex:
        client.start_db_cluster(DBClusterIdentifier="cluster-id")
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidDBClusterStateFault")
    err["Message"].should.equal("DbCluster cluster-id is not in stopped state.")


@mock_rds
def test_stop_db_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    resp = client.stop_db_cluster(DBClusterIdentifier="cluster-id")
    # Quirk of the AWS implementation - the immediate response show it's still available
    cluster = resp["DBCluster"]
    cluster["Status"].should.equal("available")
    # For some time the status will be 'stopping'
    # And finally it will be 'stopped'
    cluster = client.describe_db_clusters()["DBClusters"][0]
    cluster["Status"].should.equal("stopped")


@mock_rds
def test_stop_db_cluster_already_stopped():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    client.stop_db_cluster(DBClusterIdentifier="cluster-id")

    # can't call stop on a stopped cluster
    with pytest.raises(ClientError) as ex:
        client.stop_db_cluster(DBClusterIdentifier="cluster-id")
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidDBClusterStateFault")
    err["Message"].should.equal("DbCluster cluster-id is not in available state.")


@mock_rds
def test_stop_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.stop_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")
    err["Message"].should.equal("DBCluster cluster-unknown not found.")


@mock_rds
def test_create_db_cluster_snapshot_fails_for_unknown_cluster():
    conn = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as exc:
        conn.create_db_cluster_snapshot(
            DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
        )
    err = exc.value.response["Error"]
    err["Message"].should.equal("DBCluster db-primary-1 not found.")


@mock_rds
def test_create_db_cluster_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
    )

    snapshot = conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="g-1"
    ).get("DBClusterSnapshot")

    assert snapshot["Engine"] == "postgres"
    assert snapshot["DBClusterIdentifier"] == "db-primary-1"
    assert snapshot["DBClusterSnapshotIdentifier"] == "g-1"
    assert snapshot["SnapshotType"] == "manual"
    result = conn.list_tags_for_resource(ResourceName=snapshot["DBClusterSnapshotArn"])
    result["TagList"].should.equal([])


@mock_rds
def test_create_db_cluster_snapshot_copy_tags():
    conn = boto3.client("rds", region_name="us-west-2")

    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
        CopyTagsToSnapshot=True,
    )

    snapshot = conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="g-1"
    ).get("DBClusterSnapshot")

    snapshot.get("Engine").should.equal("postgres")
    snapshot.get("DBClusterIdentifier").should.equal("db-primary-1")
    snapshot.get("DBClusterSnapshotIdentifier").should.equal("g-1")

    result = conn.list_tags_for_resource(ResourceName=snapshot["DBClusterSnapshotArn"])
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_copy_db_cluster_snapshot_fails_for_unknown_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        conn.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="snapshot-1",
            TargetDBClusterSnapshotIdentifier="snapshot-2",
        )

    err = exc.value.response["Error"]
    err["Message"].should.equal("DBClusterSnapshot snapshot-1 not found.")


@mock_rds
def test_copy_db_cluster_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")

    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
    )

    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    ).get("DBClusterSnapshot")

    target_snapshot = conn.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier="snapshot-1",
        TargetDBClusterSnapshotIdentifier="snapshot-2",
    ).get("DBClusterSnapshot")

    target_snapshot.get("Engine").should.equal("postgres")
    target_snapshot.get("DBClusterIdentifier").should.equal("db-primary-1")
    target_snapshot.get("DBClusterSnapshotIdentifier").should.equal("snapshot-2")
    result = conn.list_tags_for_resource(
        ResourceName=target_snapshot["DBClusterSnapshotArn"]
    )
    result["TagList"].should.equal([])


@mock_rds
def test_copy_db_cluster_snapshot_fails_for_existed_target_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")

    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
    )

    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    ).get("DBClusterSnapshot")

    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-2"
    ).get("DBClusterSnapshot")

    with pytest.raises(ClientError) as exc:
        conn.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="snapshot-1",
            TargetDBClusterSnapshotIdentifier="snapshot-2",
        )

    err = exc.value.response["Error"]
    err["Message"].should.equal(
        "Cannot create the snapshot because a snapshot with the identifier snapshot-2 already exists."
    )


@mock_rds
def test_describe_db_cluster_snapshots():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
    )

    created = conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    ).get("DBClusterSnapshot")

    created.get("Engine").should.equal("postgres")

    by_database_id = conn.describe_db_cluster_snapshots(
        DBClusterIdentifier="db-primary-1"
    ).get("DBClusterSnapshots")
    by_snapshot_id = conn.describe_db_cluster_snapshots(
        DBClusterSnapshotIdentifier="snapshot-1"
    ).get("DBClusterSnapshots")
    by_snapshot_id.should.equal(by_database_id)

    snapshot = by_snapshot_id[0]
    snapshot.should.equal(created)
    snapshot.get("Engine").should.equal("postgres")

    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-2"
    )
    snapshots = conn.describe_db_cluster_snapshots(
        DBClusterIdentifier="db-primary-1"
    ).get("DBClusterSnapshots")
    snapshots.should.have.length_of(2)


@mock_rds
def test_delete_db_cluster_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
    )
    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    )

    conn.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier="snapshot-1")
    conn.delete_db_cluster_snapshot(DBClusterSnapshotIdentifier="snapshot-1")
    conn.describe_db_cluster_snapshots.when.called_with(
        DBClusterSnapshotIdentifier="snapshot-1"
    ).should.throw(ClientError)


@mock_rds
def test_restore_db_cluster_from_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
    )
    conn.describe_db_clusters()["DBClusters"].should.have.length_of(1)

    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    )

    # restore
    new_cluster = conn.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="db-restore-1",
        SnapshotIdentifier="snapshot-1",
        Engine="postgres",
    )["DBCluster"]
    new_cluster["DBClusterIdentifier"].should.equal("db-restore-1")
    new_cluster["DBClusterInstanceClass"].should.equal("db.m1.small")
    new_cluster["Engine"].should.equal("postgres")
    new_cluster["DatabaseName"].should.equal("staging-postgres")
    new_cluster["Port"].should.equal(1234)

    # Verify it exists
    conn.describe_db_clusters()["DBClusters"].should.have.length_of(2)
    conn.describe_db_clusters(DBClusterIdentifier="db-restore-1")[
        "DBClusters"
    ].should.have.length_of(1)


@mock_rds
def test_restore_db_cluster_from_snapshot_and_override_params():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
    )
    conn.describe_db_clusters()["DBClusters"].should.have.length_of(1)
    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    )

    # restore with some updated attributes
    new_cluster = conn.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="db-restore-1",
        SnapshotIdentifier="snapshot-1",
        Engine="postgres",
        Port=10000,
        DBClusterInstanceClass="db.r6g.xlarge",
    )["DBCluster"]
    new_cluster["DBClusterIdentifier"].should.equal("db-restore-1")
    new_cluster["DBClusterParameterGroup"].should.equal("default.aurora8.0")
    new_cluster["DBClusterInstanceClass"].should.equal("db.r6g.xlarge")
    new_cluster["Port"].should.equal(10000)


@mock_rds
def test_add_tags_to_cluster():
    conn = boto3.client("rds", region_name="us-west-2")
    resp = conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    cluster_arn = resp["DBCluster"]["DBClusterArn"]

    conn.add_tags_to_resource(
        ResourceName=cluster_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = conn.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    tags.should.equal([{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}])

    conn.remove_tags_from_resource(ResourceName=cluster_arn, TagKeys=["k1"])

    tags = conn.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    tags.should.equal([{"Key": "k2", "Value": "v2"}])


@mock_rds
def test_add_tags_to_cluster_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_cluster(
        DBClusterIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DatabaseName="staging-postgres",
        DBClusterInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=1234,
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    resp = conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    )
    snapshot_arn = resp["DBClusterSnapshot"]["DBClusterSnapshotArn"]

    conn.add_tags_to_resource(
        ResourceName=snapshot_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = conn.list_tags_for_resource(ResourceName=snapshot_arn)["TagList"]
    tags.should.equal([{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}])

    conn.remove_tags_from_resource(ResourceName=snapshot_arn, TagKeys=["k1"])

    tags = conn.list_tags_for_resource(ResourceName=snapshot_arn)["TagList"]
    tags.should.equal([{"Key": "k2", "Value": "v2"}])


@mock_rds
def test_create_serverless_db_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        DatabaseName="users",
        Engine="aurora-mysql",
        EngineMode="serverless",
        EngineVersion="5.6.10a",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        EnableHttpEndpoint=True,
    )
    cluster = resp["DBCluster"]
    # This is only true for specific engine versions
    cluster.should.have.key("HttpEndpointEnabled").equal(True)

    # Verify that a default serverless_configuration is added
    assert "ScalingConfigurationInfo" in cluster
    assert cluster["ScalingConfigurationInfo"]["MinCapacity"] == 1
    assert cluster["ScalingConfigurationInfo"]["MaxCapacity"] == 16


@mock_rds
def test_create_db_cluster_with_enable_http_endpoint_invalid():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        DatabaseName="users",
        Engine="aurora-mysql",
        EngineMode="serverless",
        EngineVersion="5.7.0",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        EnableHttpEndpoint=True,
    )
    cluster = resp["DBCluster"]
    # This attribute is ignored if an invalid engine version is supplied
    cluster.should.have.key("HttpEndpointEnabled").equal(False)


@mock_rds
def test_describe_db_clusters_filter_by_engine():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="id1",
        Engine="aurora-mysql",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    client.create_db_cluster(
        DBClusterIdentifier="id2",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    resp = client.describe_db_clusters(
        Filters=[
            {
                "Name": "engine",
                "Values": ["aurora-postgresql"],
            }
        ]
    )

    clusters = resp["DBClusters"]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["DBClusterIdentifier"] == "id2"
    assert cluster["Engine"] == "aurora-postgresql"


@mock_rds
def test_replicate_cluster():
    # WHEN create_db_cluster is called
    # AND create_db_cluster is called again with ReplicationSourceIdentifier set to the first cluster
    # THEN promote_read_replica_db_cluster can be called on the second cluster, elevating it to a read/write cluster
    us_east = boto3.client("rds", "us-east-1")
    us_west = boto3.client("rds", "us-west-1")

    original_arn = us_east.create_db_cluster(
        DBClusterIdentifier="dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]["DBClusterArn"]

    replica_arn = us_west.create_db_cluster(
        DBClusterIdentifier="replica_dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
        ReplicationSourceIdentifier=original_arn,
    )["DBCluster"]["DBClusterArn"]

    original = us_east.describe_db_clusters()["DBClusters"][0]
    assert original["ReadReplicaIdentifiers"] == [replica_arn]

    replica = us_west.describe_db_clusters()["DBClusters"][0]
    assert replica["ReplicationSourceIdentifier"] == original_arn
    assert replica["MultiAZ"] is True

    us_west.promote_read_replica_db_cluster(DBClusterIdentifier="replica_dbci")

    original = us_east.describe_db_clusters()["DBClusters"][0]
    assert original["ReadReplicaIdentifiers"] == []

    replica = us_west.describe_db_clusters()["DBClusters"][0]
    assert "ReplicationSourceIdentifier" not in replica
    assert replica["MultiAZ"] is False
