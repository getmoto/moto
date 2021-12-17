import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_rds2
from moto.core import ACCOUNT_ID


@mock_rds2
def test_describe_db_cluster_initial():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.describe_db_clusters()
    resp.should.have.key("DBClusters").should.have.length_of(0)


@mock_rds2
def test_create_db_cluster_needs_master_username():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="aurora")
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The parameter MasterUsername must be provided and must not be blank."
    )


@mock_rds2
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


@mock_rds2
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


@mock_rds2
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

    cluster.should.have.key("AllocatedStorage").equal(1)
    cluster.should.have.key("AvailabilityZones")
    set(cluster["AvailabilityZones"]).should.equal(
        {"eu-north-1a", "eu-north-1b", "eu-north-1c"}
    )
    cluster.should.have.key("BackupRetentionPeriod").equal(1)
    cluster.should.have.key("DBClusterIdentifier").equal("cluster-id")
    cluster.should.have.key("DBClusterParameterGroup").equal("default.aurora5.6")
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


@mock_rds2
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
    cluster.should.have.key("DBClusterParameterGroup").equal("default.aurora5.6")


@mock_rds2
def test_create_db_cluster_additional_parameters():
    client = boto3.client("rds", region_name="eu-north-1")

    resp = client.create_db_cluster(
        AvailabilityZones=["eu-north-1b"],
        DBClusterIdentifier="cluster-id",
        Engine="aurora",
        EngineVersion="5.6.mysql_aurora.1.19.2",
        EngineMode="serverless",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        Port=1234,
        DeletionProtection=True,
    )

    cluster = resp["DBCluster"]

    cluster.should.have.key("AvailabilityZones").equal(["eu-north-1b"])
    cluster.should.have.key("Engine").equal("aurora")
    cluster.should.have.key("EngineVersion").equal("5.6.mysql_aurora.1.19.2")
    cluster.should.have.key("EngineMode").equal("serverless")
    cluster.should.have.key("Port").equal(1234)
    cluster.should.have.key("DeletionProtection").equal(True)


@mock_rds2
def test_describe_db_cluster_after_creation():
    client = boto3.client("rds", region_name="eu-north-1")

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id1",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id2",
        Engine="aurora",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    client.describe_db_clusters()["DBClusters"].should.have.length_of(2)

    client.describe_db_clusters(DBClusterIdentifier="cluster-id2")[
        "DBClusters"
    ].should.have.length_of(1)


@mock_rds2
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


@mock_rds2
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


@mock_rds2
def test_delete_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.delete_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")
    err["Message"].should.equal("DBCluster cluster-unknown not found.")


@mock_rds2
def test_start_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.start_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")
    err["Message"].should.equal("DBCluster cluster-unknown not found.")


@mock_rds2
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


@mock_rds2
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


@mock_rds2
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


@mock_rds2
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


@mock_rds2
def test_stop_db_cluster_unknown_cluster():
    client = boto3.client("rds", region_name="eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.stop_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")
    err["Message"].should.equal("DBCluster cluster-unknown not found.")
