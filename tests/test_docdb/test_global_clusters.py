import boto3

from moto import mock_aws


@mock_aws
def test_describe():
    client = boto3.client("docdb", "us-east-2")
    assert client.describe_global_clusters()["GlobalClusters"] == []


@mock_aws
def test_create_global_cluster():
    client = boto3.client("docdb", "us-east-1")
    resp = client.create_global_cluster(GlobalClusterIdentifier="g-id", Engine="docdb")[
        "GlobalCluster"
    ]
    assert resp["GlobalClusterIdentifier"] == "g-id"
    assert "GlobalClusterResourceId" in resp
    assert "GlobalClusterArn" in resp
    assert resp["Engine"] == "docdb"
    assert resp["EngineVersion"] == "5.0.0"
    assert resp["StorageEncrypted"] is False
    assert resp["DeletionProtection"] is False

    assert len(client.describe_global_clusters()["GlobalClusters"]) == 1

    # As a global cluster, verify it can be retrieved everywhere
    europe_client = boto3.client("docdb", "eu-north-1")
    assert len(europe_client.describe_global_clusters()["GlobalClusters"]) == 1


@mock_aws
def test_create_global_cluster_with_additional_params():
    client = boto3.client("docdb", "us-east-1")
    resp = client.create_global_cluster(
        GlobalClusterIdentifier="g-id",
        Engine="docdb",
        EngineVersion="4.0.0",
        DeletionProtection=True,
        StorageEncrypted=True,
    )["GlobalCluster"]
    assert resp["Engine"] == "docdb"
    assert resp["EngineVersion"] == "4.0.0"
    assert resp["StorageEncrypted"] is True
    assert resp["DeletionProtection"] is True


@mock_aws
def test_create_global_cluster_from_source_cluster():
    client = boto3.client("docdb", "us-east-1")
    cluster_arn = client.create_db_cluster(
        DBClusterIdentifier="primary",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )["DBCluster"]["DBClusterArn"]
    resp = client.create_global_cluster(
        GlobalClusterIdentifier="g-id", SourceDBClusterIdentifier=cluster_arn
    )["GlobalCluster"]
    assert resp["Engine"] == "docdb"
    assert resp["EngineVersion"] == "5.0.0"
    assert len(resp["GlobalClusterMembers"]) == 1
    assert resp["GlobalClusterMembers"][0]["DBClusterArn"] == cluster_arn

    cluster = client.describe_db_clusters(DBClusterIdentifier="primary")["DBClusters"][
        0
    ]
    assert cluster["DBClusterIdentifier"] == "primary"


@mock_aws
def test_delete_global_cluster():
    client = boto3.client("docdb", "us-east-2")
    client.create_global_cluster(GlobalClusterIdentifier="g-id2", Engine="docdb")

    client.delete_global_cluster(GlobalClusterIdentifier="g-id2")

    assert client.describe_global_clusters()["GlobalClusters"] == []
