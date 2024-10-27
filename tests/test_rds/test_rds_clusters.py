import re

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

RDS_REGION = "eu-north-1"


@mock_aws
def test_describe_db_cluster_initial():
    client = boto3.client("rds", region_name=RDS_REGION)

    resp = client.describe_db_clusters()
    assert len(resp["DBClusters"]) == 0


@mock_aws
def test_describe_db_cluster_fails_for_non_existent_cluster():
    client = boto3.client("rds", region_name=RDS_REGION)

    resp = client.describe_db_clusters()
    assert len(resp["DBClusters"]) == 0
    with pytest.raises(ClientError) as ex:
        client.describe_db_clusters(DBClusterIdentifier="cluster-id")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-id not found."


@mock_aws
def test_create_db_cluster_invalid_engine():
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id", Engine="aurora-postgresql"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUsername must be provided and must not be blank."
    )


@mock_aws
def test_create_db_cluster_needs_master_username():
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id", Engine="aurora-postgresql"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUsername must be provided and must not be blank."
    )


@mock_aws
def test_create_db_cluster_needs_master_user_password():
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id",
            Engine="aurora-postgresql",
            MasterUsername="root",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUserPassword must be provided and must not be blank."
    )


@mock_aws
def test_create_db_cluster_needs_long_master_user_password():
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id",
            Engine="aurora-postgresql",
            MasterUsername="root",
            MasterUserPassword="hunter2",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUserPassword is not a valid password because "
        "it is shorter than 8 characters."
    )


@mock_aws
def test_modify_db_cluster_needs_long_master_user_password():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster(
            DBClusterIdentifier="cluster-id",
            MasterUserPassword="hunter2",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUserPassword is not a valid password because "
        "it is shorter than 8 characters."
    )


@mock_aws
def test_modify_db_cluster_new_cluster_identifier():
    client = boto3.client("rds", region_name=RDS_REGION)
    old_id = "cluster-id"
    new_id = "new-cluster-id"

    client.create_db_cluster(
        DBClusterIdentifier=old_id,
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    resp = client.modify_db_cluster(
        DBClusterIdentifier=old_id,
        NewDBClusterIdentifier=new_id,
        MasterUserPassword="hunter21",
    )

    assert resp["DBCluster"]["DBClusterIdentifier"] == new_id

    clusters = [
        cluster["DBClusterIdentifier"]
        for cluster in client.describe_db_clusters()["DBClusters"]
    ]

    assert old_id not in clusters


@mock_aws
def test_create_db_cluster__verify_default_properties():
    client = boto3.client("rds", region_name=RDS_REGION)

    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-mysql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    assert "DBCluster" in resp

    cluster = resp["DBCluster"]

    # This was not supplied, so should not be returned
    assert "DatabaseName" not in cluster

    assert "AvailabilityZones" in cluster
    assert set(cluster["AvailabilityZones"]) == {
        "eu-north-1a",
        "eu-north-1b",
        "eu-north-1c",
    }
    assert cluster["BackupRetentionPeriod"] == 1
    assert cluster["DBClusterIdentifier"] == "cluster-id"
    assert cluster["DBClusterParameterGroup"] == "default.aurora8.0"
    assert cluster["DBSubnetGroup"] == "default"
    assert cluster["Status"] == "creating"
    assert re.match(
        "cluster-id.cluster-[a-z0-9]{12}.eu-north-1.rds.amazonaws.com",
        cluster["Endpoint"],
    )
    endpoint = cluster["Endpoint"]
    expected_readonly = endpoint.replace(
        "cluster-id.cluster-", "cluster-id.cluster-ro-"
    )
    assert cluster["ReaderEndpoint"] == expected_readonly
    assert cluster["MultiAZ"] is False
    assert cluster["Engine"] == "aurora-mysql"
    assert cluster["EngineVersion"] == "5.7.mysql_aurora.2.07.2"
    assert cluster["Port"] == 3306
    assert cluster["MasterUsername"] == "root"
    assert cluster["PreferredBackupWindow"] == "01:37-02:07"
    assert cluster["PreferredMaintenanceWindow"] == "wed:02:40-wed:03:10"
    assert cluster["ReadReplicaIdentifiers"] == []
    assert cluster["DBClusterMembers"] == []
    assert "VpcSecurityGroups" in cluster
    assert "HostedZoneId" in cluster
    assert cluster["StorageEncrypted"] is False
    assert re.match(r"cluster-[A-Z0-9]{26}", cluster["DbClusterResourceId"])
    assert cluster["DBClusterArn"] == (
        f"arn:aws:rds:eu-north-1:{ACCOUNT_ID}:cluster:cluster-id"
    )
    assert cluster["AssociatedRoles"] == []
    assert cluster["IAMDatabaseAuthenticationEnabled"] is False
    assert cluster["EngineMode"] == "provisioned"
    assert cluster["DeletionProtection"] is False
    assert cluster["HttpEndpointEnabled"] is False
    assert cluster["CopyTagsToSnapshot"] is False
    assert cluster["CrossAccountClone"] is False
    assert cluster["DeletionProtection"] is False
    assert cluster["DomainMemberships"] == []
    assert cluster["TagList"] == []
    assert "ClusterCreateTime" in cluster
    assert cluster["EarliestRestorableTime"] >= cluster["ClusterCreateTime"]
    assert cluster["StorageEncrypted"] is False
    assert cluster["GlobalWriteForwardingRequested"] is False


@mock_aws
def test_create_db_cluster_additional_parameters():
    client = boto3.client("rds", region_name=RDS_REGION)

    resp = client.create_db_cluster(
        AvailabilityZones=["eu-north-1b"],
        DatabaseName="users",
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
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
        StorageEncrypted=True,
        EnableGlobalWriteForwarding=True,
        ScalingConfiguration={
            "MinCapacity": 5,
            "AutoPause": True,
        },
        ServerlessV2ScalingConfiguration={
            "MinCapacity": 2,
            "MaxCapacity": 4,
        },
        VpcSecurityGroupIds=["sg1", "sg2"],
        EnableIAMDatabaseAuthentication=True,
    )

    cluster = resp["DBCluster"]

    assert cluster["AvailabilityZones"] == ["eu-north-1b"]
    assert cluster["DatabaseName"] == "users"
    assert cluster["Engine"] == "aurora-postgresql"
    assert cluster["EngineVersion"] == "8.0.mysql_aurora.3.01.0"
    assert cluster["EngineMode"] == "serverless"
    assert cluster["Port"] == 1234
    assert cluster["DeletionProtection"] is True
    assert cluster["EnabledCloudwatchLogsExports"] == ["audit"]
    assert cluster["KmsKeyId"] == "some:kms:arn"
    assert cluster["NetworkType"] == "IPV4"
    assert cluster["DBSubnetGroup"] == "subnetgroupname"
    assert cluster["StorageEncrypted"] is True
    assert cluster["GlobalWriteForwardingRequested"] is True
    assert cluster["ScalingConfigurationInfo"] == {"MinCapacity": 5, "AutoPause": True}
    assert cluster["ServerlessV2ScalingConfiguration"] == {
        "MaxCapacity": 4.0,
        "MinCapacity": 2.0,
    }

    security_groups = cluster["VpcSecurityGroups"]
    assert len(security_groups) == 2
    assert {"VpcSecurityGroupId": "sg1", "Status": "active"} in security_groups
    assert {"VpcSecurityGroupId": "sg2", "Status": "active"} in security_groups
    assert cluster["IAMDatabaseAuthenticationEnabled"] is True


@mock_aws
def test_describe_db_cluster_after_creation():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id1",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    cluster_arn = client.create_db_cluster(
        DBClusterIdentifier="cluster-id2",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )["DBCluster"]["DBClusterArn"]

    assert len(client.describe_db_clusters()["DBClusters"]) == 2

    assert (
        len(
            client.describe_db_clusters(DBClusterIdentifier="cluster-id2")["DBClusters"]
        )
        == 1
    )

    assert (
        len(client.describe_db_clusters(DBClusterIdentifier=cluster_arn)["DBClusters"])
        == 1
    )


@mock_aws
def test_delete_db_cluster():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    client.delete_db_cluster(DBClusterIdentifier="cluster-id")

    assert len(client.describe_db_clusters()["DBClusters"]) == 0


@mock_aws
def test_delete_db_cluster_do_snapshot():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    client.delete_db_cluster(
        DBClusterIdentifier="cluster-id", FinalDBSnapshotIdentifier="final-snapshot"
    )
    assert len(client.describe_db_clusters()["DBClusters"]) == 0
    snapshot = client.describe_db_cluster_snapshots()["DBClusterSnapshots"][0]
    assert snapshot["DBClusterIdentifier"] == "cluster-id"
    assert snapshot["DBClusterSnapshotIdentifier"] == "final-snapshot"
    assert snapshot["SnapshotType"] == "automated"


@mock_aws
def test_delete_db_cluster_that_is_protected():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        DeletionProtection=True,
    )

    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier="cluster-id")
    err = exc.value.response["Error"]
    assert err["Message"] == "Can't delete Cluster with protection enabled"


@mock_aws
def test_delete_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.delete_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-unknown not found."


@mock_aws
def test_start_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.start_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-unknown not found."


@mock_aws
def test_start_db_cluster_after_stopping():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    client.stop_db_cluster(DBClusterIdentifier="cluster-id")

    client.start_db_cluster(DBClusterIdentifier="cluster-id")
    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert cluster["Status"] == "available"


@mock_aws
def test_start_db_cluster_without_stopping():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    with pytest.raises(ClientError) as ex:
        client.start_db_cluster(DBClusterIdentifier="cluster-id")
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidDBClusterStateFault"
    assert err["Message"] == "DbCluster cluster-id is not in stopped state."


@mock_aws
def test_stop_db_cluster():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    resp = client.stop_db_cluster(DBClusterIdentifier="cluster-id")
    # Quirk of the AWS implementation - the immediate response show it's still available
    cluster = resp["DBCluster"]
    assert cluster["Status"] == "available"
    # For some time the status will be 'stopping'
    # And finally it will be 'stopped'
    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert cluster["Status"] == "stopped"


@mock_aws
def test_stop_db_cluster_already_stopped():
    client = boto3.client("rds", region_name=RDS_REGION)

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    client.stop_db_cluster(DBClusterIdentifier="cluster-id")

    # can't call stop on a stopped cluster
    with pytest.raises(ClientError) as ex:
        client.stop_db_cluster(DBClusterIdentifier="cluster-id")
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidDBClusterStateFault"
    assert err["Message"] == "DbCluster cluster-id is not in available state."


@mock_aws
def test_stop_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.stop_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-unknown not found."


@mock_aws
def test_create_db_cluster_snapshot_fails_for_unknown_cluster():
    conn = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as exc:
        conn.create_db_cluster_snapshot(
            DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
        )
    err = exc.value.response["Error"]
    assert err["Message"] == "DBCluster db-primary-1 not found."


@mock_aws
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
    assert result["TagList"] == []


@mock_aws
def test_create_db_cluster_snapshot_copy_tags():
    conn = boto3.client("rds", region_name="us-west-2")

    dbci = "db-primary-1"
    conn.create_db_cluster(
        DBClusterIdentifier=dbci,
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
        DBClusterIdentifier=dbci, DBClusterSnapshotIdentifier="g-1"
    ).get("DBClusterSnapshot")

    assert snapshot.get("Engine") == "postgres"
    assert snapshot.get("DBClusterIdentifier") == dbci
    assert snapshot.get("DBClusterSnapshotIdentifier") == "g-1"

    result = conn.list_tags_for_resource(ResourceName=snapshot["DBClusterSnapshotArn"])
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]

    snapshot = conn.describe_db_cluster_snapshots(DBClusterIdentifier=dbci)[
        "DBClusterSnapshots"
    ][0]
    assert snapshot["TagList"] == [
        {"Key": "foo", "Value": "bar"},
        {"Key": "foo1", "Value": "bar1"},
    ]


@mock_aws
def test_copy_db_cluster_snapshot_fails_for_unknown_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")

    with pytest.raises(ClientError) as exc:
        conn.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="snapshot-1",
            TargetDBClusterSnapshotIdentifier="snapshot-2",
        )

    err = exc.value.response["Error"]
    assert err["Message"] == "DBClusterSnapshot snapshot-1 not found."


@mock_aws
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

    assert target_snapshot.get("Engine") == "postgres"
    assert target_snapshot.get("DBClusterIdentifier") == "db-primary-1"
    assert target_snapshot.get("DBClusterSnapshotIdentifier") == "snapshot-2"
    result = conn.list_tags_for_resource(
        ResourceName=target_snapshot["DBClusterSnapshotArn"]
    )
    assert result["TagList"] == []


@mock_aws
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
    assert err["Message"] == (
        "Cannot create the snapshot because a snapshot with the identifier "
        "snapshot-2 already exists."
    )


@mock_aws
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

    assert created.get("Engine") == "postgres"

    by_database_id = conn.describe_db_cluster_snapshots(
        DBClusterIdentifier="db-primary-1"
    ).get("DBClusterSnapshots")
    by_snapshot_id = conn.describe_db_cluster_snapshots(
        DBClusterSnapshotIdentifier="snapshot-1"
    ).get("DBClusterSnapshots")
    assert by_snapshot_id == by_database_id

    snapshot = by_snapshot_id[0]
    assert snapshot == created
    assert snapshot.get("Engine") == "postgres"

    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-2"
    )
    snapshots = conn.describe_db_cluster_snapshots(
        DBClusterIdentifier="db-primary-1"
    ).get("DBClusterSnapshots")
    assert len(snapshots) == 2


@mock_aws
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
    with pytest.raises(ClientError):
        conn.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier="snapshot-1")


@mock_aws
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
    assert len(conn.describe_db_clusters()["DBClusters"]) == 1

    conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    )

    # restore
    new_cluster = conn.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="db-restore-1",
        SnapshotIdentifier="snapshot-1",
        Engine="postgres",
    )["DBCluster"]
    assert new_cluster["DBClusterIdentifier"] == "db-restore-1"
    assert new_cluster["DBClusterInstanceClass"] == "db.m1.small"
    assert new_cluster["Engine"] == "postgres"
    assert new_cluster["DatabaseName"] == "staging-postgres"
    assert new_cluster["Port"] == 1234

    # Verify it exists
    assert len(conn.describe_db_clusters()["DBClusters"]) == 2
    assert (
        len(conn.describe_db_clusters(DBClusterIdentifier="db-restore-1")["DBClusters"])
        == 1
    )


@mock_aws
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
    assert len(conn.describe_db_clusters()["DBClusters"]) == 1
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
    assert new_cluster["DBClusterIdentifier"] == "db-restore-1"
    assert new_cluster["DBClusterParameterGroup"] == "default.aurora8.0"
    assert new_cluster["DBClusterInstanceClass"] == "db.r6g.xlarge"
    assert new_cluster["Port"] == 10000


@mock_aws
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
    assert tags == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

    conn.remove_tags_from_resource(ResourceName=cluster_arn, TagKeys=["k1"])

    tags = conn.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}]


@mock_aws
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
        CopyTagsToSnapshot=True,
    )
    resp = conn.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
    )
    snapshot_arn = resp["DBClusterSnapshot"]["DBClusterSnapshotArn"]

    conn.add_tags_to_resource(
        ResourceName=snapshot_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = conn.list_tags_for_resource(ResourceName=snapshot_arn)["TagList"]
    assert tags == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

    conn.remove_tags_from_resource(ResourceName=snapshot_arn, TagKeys=["k1"])

    tags = conn.list_tags_for_resource(ResourceName=snapshot_arn)["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}]


@mock_aws
def test_create_serverless_db_cluster():
    client = boto3.client("rds", region_name=RDS_REGION)

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
    assert cluster["HttpEndpointEnabled"] is True

    # Verify that a default serverless_configuration is added
    assert "ScalingConfigurationInfo" in cluster
    assert cluster["ScalingConfigurationInfo"]["MinCapacity"] == 1
    assert cluster["ScalingConfigurationInfo"]["MaxCapacity"] == 16


@mock_aws
def test_create_db_cluster_with_enable_http_endpoint_invalid():
    client = boto3.client("rds", region_name=RDS_REGION)

    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        DatabaseName="users",
        Engine="aurora-postgresql",
        EngineMode="serverless",
        EngineVersion="5.7.0",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        EnableHttpEndpoint=True,
    )
    cluster = resp["DBCluster"]
    # This attribute is ignored if an invalid engine version is supplied
    assert cluster["HttpEndpointEnabled"] is False


@mock_aws
def test_describe_db_clusters_filter_by_engine():
    client = boto3.client("rds", region_name=RDS_REGION)

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


@mock_aws
def test_replicate_cluster():
    # WHEN create_db_cluster is called
    # AND create_db_cluster is called again with ReplicationSourceIdentifier
    #    set to the first cluster
    # THEN promote_read_replica_db_cluster can be called on the second
    #    cluster, elevating it to a read/write cluster
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


@mock_aws
def test_createdb_instance_engine_mismatch_fail():
    # Setup
    client = boto3.client("rds", "us-east-1")
    cluster_name = "test-cluster"
    client.create_db_cluster(
        DBClusterIdentifier=cluster_name,
        Engine="aurora-postgresql",
        EngineVersion="12.14",
        MasterUsername="testuser",
        MasterUserPassword="password",
    )

    # Execute

    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            DBClusterIdentifier=cluster_name,
            Engine="mysql",
            EngineVersion="12.14",
            DBInstanceIdentifier="test-instance",
            DBInstanceClass="db.t4g.medium",
        )

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "The engine name requested for your DB instance (mysql) doesn't match "
        "the engine name of your DB cluster (aurora-postgresql)."
    )


@mock_aws
def test_describe_db_cluster_snapshot_attributes_default():
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
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="g-1"
    ).get("DBClusterSnapshot")

    resp = conn.describe_db_cluster_snapshot_attributes(
        DBClusterSnapshotIdentifier="g-1"
    )

    assert (
        resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotIdentifier"]
        == "g-1"
    )
    assert (
        resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotAttributes"] == []
    )


@mock_aws
def test_describe_db_cluster_snapshot_attributes():
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
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="g-1"
    ).get("DBClusterSnapshot")

    conn.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToAdd=["test", "test2"],
    )

    resp = conn.describe_db_cluster_snapshot_attributes(
        DBClusterSnapshotIdentifier="g-1"
    )

    assert (
        resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotIdentifier"]
        == "g-1"
    )
    assert (
        resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotAttributes"][0][
            "AttributeName"
        ]
        == "restore"
    )
    assert resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotAttributes"][0][
        "AttributeValues"
    ] == ["test", "test2"]


@mock_aws
def test_modify_db_cluster_snapshot_attribute():
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
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="g-1"
    ).get("DBClusterSnapshot")

    resp = conn.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToAdd=["test", "test2"],
    )
    resp = conn.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToRemove=["test"],
    )
    resp = conn.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToAdd=["test3"],
    )
    assert (
        resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotIdentifier"]
        == "g-1"
    )
    assert (
        resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotAttributes"][0][
            "AttributeName"
        ]
        == "restore"
    )
    assert resp["DBClusterSnapshotAttributesResult"]["DBClusterSnapshotAttributes"][0][
        "AttributeValues"
    ] == ["test2", "test3"]


@mock_aws
def test_backtrack_window():
    client = boto3.client("rds", region_name=RDS_REGION)
    window = 86400
    resp = client.create_db_cluster(
        AvailabilityZones=["eu-north-1b"],
        DatabaseName="users",
        DBClusterIdentifier="cluster-id",
        Engine="aurora-mysql",
        EngineVersion="8.0.mysql_aurora.3.01.0",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        Port=1234,
        DeletionProtection=True,
        EnableCloudwatchLogsExports=["audit"],
        NetworkType="IPV4",
        DBSubnetGroupName="subnetgroupname",
        StorageEncrypted=True,
        VpcSecurityGroupIds=["sg1", "sg2"],
        BacktrackWindow=window,
    )

    assert resp["DBCluster"]["BacktrackWindow"] == window


@mock_aws
@pytest.mark.parametrize(
    "params",
    [
        (
            "aurora-mysql",
            -1,
            "The specified value (-1) is not a valid Backtrack Window. Allowed values are within the range of 0 to 259200",
        ),
        (
            "aurora-mysql",
            10000000,
            "The specified value (10000000) is not a valid Backtrack Window. Allowed values are within the range of 0 to 259200",
        ),
        (
            "aurora-postgresql",
            20,
            "Backtrack is not enabled for the postgres engine.",
        ),
    ],
)
def test_backtrack_errors(params):
    client = boto3.client("rds", region_name=RDS_REGION)

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            AvailabilityZones=["eu-north-1b"],
            DatabaseName="users",
            DBClusterIdentifier="cluster-id",
            Engine=params[0],
            EngineVersion="8.0.mysql_aurora.3.01.0",
            MasterUsername="root",
            MasterUserPassword="hunter2_",
            DBSubnetGroupName="subnetgroupname",
            StorageEncrypted=True,
            VpcSecurityGroupIds=["sg1", "sg2"],
            BacktrackWindow=params[1],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == params[2]
