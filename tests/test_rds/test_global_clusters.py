import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID


@mock_aws
def test_create_global_cluster__not_enough_parameters():
    client = boto3.client("rds", "us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_global_cluster(GlobalClusterIdentifier="gc1")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "When creating standalone global cluster, value for engineName should be specified"
    )


@mock_aws
def test_global_cluster_members():
    # WHEN create_global_cluster is called
    # AND create_db_cluster is called with GlobalClusterIdentifier set to the global cluster ARN
    # THEN describe_global_cluster shows the second cluster as part of the GlobalClusterMembers
    # AND describe_db_clusters shows the cluster as normal
    client = boto3.client("rds", "us-east-1")

    global_cluster = client.create_global_cluster(
        GlobalClusterIdentifier="gc1", Engine="aurora-mysql"
    )["GlobalCluster"]
    assert global_cluster["GlobalClusterIdentifier"] == "gc1"
    assert "GlobalClusterResourceId" in global_cluster
    assert (
        global_cluster["GlobalClusterArn"]
        == f"arn:aws:rds::{DEFAULT_ACCOUNT_ID}:global-cluster:gc1"
    )
    assert global_cluster["Status"] == "available"
    assert global_cluster["Engine"] == "aurora-mysql"
    assert "mysql_aurora" in global_cluster["EngineVersion"]
    assert global_cluster["StorageEncrypted"] is False
    assert global_cluster["DeletionProtection"] is False
    assert global_cluster["GlobalClusterMembers"] == []

    resp = client.create_db_cluster(
        DBClusterIdentifier="dbci",
        GlobalClusterIdentifier="gc1",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]
    cluster_arn = resp["DBClusterArn"]

    resp = client.describe_global_clusters(GlobalClusterIdentifier="gc1")
    assert len(resp["GlobalClusters"]) == 1
    global_cluster = resp["GlobalClusters"][0]
    assert global_cluster["GlobalClusterIdentifier"] == "gc1"

    assert len(global_cluster["GlobalClusterMembers"]) == 1
    assert global_cluster["GlobalClusterMembers"][0]["DBClusterArn"] == cluster_arn


@mock_aws
def test_create_global_cluster_from_regular_cluster():
    # WHEN create_db_cluster is called
    # AND create_global_cluster is called with SourceDBClusterIdentifier
    #     set as the earlier created db cluster
    # THEN that db cluster is elevated to a global cluster
    # AND it still shows up when calling describe_db_clusters
    client = boto3.client("rds", "us-east-1")

    resp = client.create_db_cluster(
        DBClusterIdentifier="dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]
    cluster_arn = resp["DBClusterArn"]

    client.create_global_cluster(
        GlobalClusterIdentifier="gc1", SourceDBClusterIdentifier=cluster_arn
    )

    resp = client.describe_global_clusters(GlobalClusterIdentifier="gc1")
    assert len(resp["GlobalClusters"]) == 1
    global_cluster = resp["GlobalClusters"][0]
    assert global_cluster["GlobalClusterIdentifier"] == "gc1"

    assert len(global_cluster["GlobalClusterMembers"]) == 1
    assert global_cluster["GlobalClusterMembers"][0]["DBClusterArn"] == cluster_arn


@mock_aws
def test_create_global_cluster_from_regular_cluster_with_reader():
    east_client = boto3.client("rds", "eu-west-1")
    west_client = boto3.client("rds", "eu-west-2")

    # Create global cluster
    east_client.create_global_cluster(
        GlobalClusterIdentifier="test-global-db",
        Engine="aurora-mysql",
        DeletionProtection=False,
        DatabaseName="test-db",
        StorageEncrypted=False,
    )

    east_client.create_db_cluster(
        DBClusterIdentifier="test-primary-cluster",
        Engine="aurora-mysql",
        GlobalClusterIdentifier="test-global-db",
        MasterUsername="testUsername",
        MasterUserPassword="testPassword",
    )

    east_client.create_db_instance(
        DBInstanceIdentifier="test-primary-cluster-i1",
        DBInstanceClass="db.r5.large",
        Engine="aurora-mysql",
        PubliclyAccessible=False,
        DBClusterIdentifier="test-primary-cluster",
    )

    west_client.create_db_cluster(
        DBClusterIdentifier="test-secondary-cluster",
        Engine="aurora-mysql",
        GlobalClusterIdentifier="test-global-db",
    )

    resp = east_client.describe_global_clusters(
        GlobalClusterIdentifier="test-global-db"
    )
    members = resp["GlobalClusters"][0]["GlobalClusterMembers"]
    assert len(members) == 2
    assert (
        members[0]["DBClusterArn"]
        == "arn:aws:rds:eu-west-1:123456789012:cluster:test-primary-cluster"
    )
    assert len(members[0]["Readers"]) == 1
    assert (
        members[0]["Readers"][0]
        == "arn:aws:rds:eu-west-2:123456789012:cluster:test-secondary-cluster"
    )
    assert members[0]["IsWriter"]

    assert (
        members[1]["DBClusterArn"]
        == "arn:aws:rds:eu-west-2:123456789012:cluster:test-secondary-cluster"
    )
    assert len(members[1]["Readers"]) == 0
    assert not members[1]["IsWriter"]


@mock_aws
def test_create_global_cluster_from_regular_cluster__using_name():
    client = boto3.client("rds", "us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_global_cluster(
            GlobalClusterIdentifier="gc1", SourceDBClusterIdentifier="dbci"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Malformed db cluster arn dbci"


@mock_aws
def test_create_global_cluster_from_regular_cluster__and_specify_engine():
    client = boto3.client("rds", "us-east-1")

    resp = client.create_db_cluster(
        DBClusterIdentifier="dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]
    cluster_arn = resp["DBClusterArn"]

    with pytest.raises(ClientError) as exc:
        client.create_global_cluster(
            GlobalClusterIdentifier="gc1",
            Engine="aurora-mysql",
            SourceDBClusterIdentifier=cluster_arn,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert err["Message"] == (
        "When creating global cluster from existing db cluster, value for "
        "engineName should not be specified since it will be inherited "
        "from source cluster"
    )


@mock_aws
def test_delete_non_global_cluster():
    # WHEN a global cluster contains a regular cluster
    # AND we attempt to delete the global cluster
    # THEN we get an error message
    # An error occurs (InvalidGlobalClusterStateFault) when calling the
    #    DeleteGlobalCluster operation: Global Cluster
    #    arn:aws:rds::486285699788:global-cluster:g1 is not empty
    client = boto3.client("rds", "us-east-1")

    client.create_global_cluster(GlobalClusterIdentifier="gc1", Engine="aurora-mysql")
    _ = client.create_db_cluster(
        DBClusterIdentifier="dbci",
        GlobalClusterIdentifier="gc1",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]

    with pytest.raises(ClientError) as exc:
        client.delete_global_cluster(GlobalClusterIdentifier="gc1")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidGlobalClusterStateFault"
    assert (
        err["Message"]
        == f"Global Cluster arn:aws:rds::{DEFAULT_ACCOUNT_ID}:global-cluster:gc1 is not empty"
    )

    # Delete the child first
    client.delete_db_cluster(DBClusterIdentifier="dbci")

    # Then we can delete the global cluster
    client.delete_global_cluster(GlobalClusterIdentifier="gc1")

    assert client.describe_global_clusters()["GlobalClusters"] == []


@mock_aws
def test_remove_from_global_cluster():
    client = boto3.client("rds", "us-east-1")

    client.create_global_cluster(GlobalClusterIdentifier="gc1", Engine="aurora-mysql")

    # Assign to the global cluster
    client.create_db_cluster(
        DBClusterIdentifier="dbci",
        GlobalClusterIdentifier="gc1",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )

    # Remove it again
    client.remove_from_global_cluster(
        GlobalClusterIdentifier="gc1",
        DbClusterIdentifier="dbci",
    )

    # Verify it's been removed
    resp = client.describe_global_clusters(GlobalClusterIdentifier="gc1")

    assert len(resp["GlobalClusters"][0]["GlobalClusterMembers"]) == 0

    # Verifying a global cluster that doesn't exist, should fail silently
    client.remove_from_global_cluster(
        GlobalClusterIdentifier="gc1",
        DbClusterIdentifier="dbci",
    )
