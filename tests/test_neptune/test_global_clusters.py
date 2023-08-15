import boto3
from moto import mock_neptune


@mock_neptune
def test_describe():
    client = boto3.client("neptune", "us-east-2")
    assert client.describe_global_clusters()["GlobalClusters"] == []


@mock_neptune
def test_create_global_cluster():
    client = boto3.client("neptune", "us-east-1")
    resp = client.create_global_cluster(
        GlobalClusterIdentifier="g-id", Engine="neptune"
    )["GlobalCluster"]
    assert resp["GlobalClusterIdentifier"] == "g-id"
    assert "GlobalClusterResourceId" in resp
    assert "GlobalClusterArn" in resp
    assert resp["Engine"] == "neptune"
    assert resp["EngineVersion"] == "1.2.0.0"
    assert resp["StorageEncrypted"] is False
    assert resp["DeletionProtection"] is False

    assert len(client.describe_global_clusters()["GlobalClusters"]) == 1

    # As a global cluster, verify it can be retrieved everywhere
    europe_client = boto3.client("neptune", "eu-north-1")
    assert len(europe_client.describe_global_clusters()["GlobalClusters"]) == 1


@mock_neptune
def test_create_global_cluster_with_additional_params():
    client = boto3.client("neptune", "us-east-1")
    resp = client.create_global_cluster(
        GlobalClusterIdentifier="g-id",
        Engine="neptune",
        EngineVersion="1.0",
        DeletionProtection=True,
        StorageEncrypted=True,
    )["GlobalCluster"]
    assert resp["Engine"] == "neptune"
    assert resp["EngineVersion"] == "1.0"
    assert resp["StorageEncrypted"] is True
    assert resp["DeletionProtection"] is True


@mock_neptune
def test_delete_global_cluster():
    client = boto3.client("neptune", "us-east-2")
    client.create_global_cluster(GlobalClusterIdentifier="g-id2", Engine="neptune")

    client.delete_global_cluster(GlobalClusterIdentifier="g-id2")

    assert client.describe_global_clusters()["GlobalClusters"] == []
