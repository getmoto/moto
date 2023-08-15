"""Unit tests for neptune-supported APIs."""
import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_neptune

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_neptune
def test_create_db_cluster():
    client = boto3.client("neptune", region_name="us-east-2")
    resp = client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")[
        "DBCluster"
    ]
    assert resp["DBClusterIdentifier"] == "cluster-id"
    assert "DbClusterResourceId" in resp
    assert "DBClusterArn" in resp
    assert resp["Engine"] == "neptune"
    assert resp["EngineVersion"] == "1.2.0.2"
    assert resp["StorageEncrypted"] is True
    assert resp["DBClusterParameterGroup"] == ""
    assert "Endpoint" in resp
    assert "cluster-" in resp["DbClusterResourceId"]
    assert resp["AvailabilityZones"] == ["us-east-2a", "us-east-2b", "us-east-2c"]
    assert "ServerlessV2ScalingConfiguration" not in resp

    # Double check this cluster is not available in another region
    europe_client = boto3.client("neptune", region_name="eu-west-2")
    assert len(europe_client.describe_db_clusters()["DBClusters"]) == 0


@mock_neptune
def test_create_db_cluster__with_additional_params():
    client = boto3.client("neptune", region_name="us-east-1")
    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="neptune",
        EngineVersion="1.1.0.1",
        StorageEncrypted=False,
        DBClusterParameterGroupName="myprm",
        KmsKeyId="key",
        ServerlessV2ScalingConfiguration={"MinCapacity": 1.0, "MaxCapacity": 2.0},
        DatabaseName="sth",
    )["DBCluster"]
    assert resp["StorageEncrypted"] is False
    assert resp["DBClusterParameterGroup"] == "myprm"
    assert resp["EngineVersion"] == "1.1.0.1"
    assert resp["KmsKeyId"] == "key"
    assert resp["ServerlessV2ScalingConfiguration"] == {
        "MinCapacity": 1.0,
        "MaxCapacity": 2.0,
    }
    assert resp["DatabaseName"] == "sth"


@mock_neptune
def test_describe_db_clusters():
    client = boto3.client("neptune", region_name="ap-southeast-1")
    assert client.describe_db_clusters()["DBClusters"] == []

    client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")

    clusters = client.describe_db_clusters(DBClusterIdentifier="cluster-id")[
        "DBClusters"
    ]
    assert len(clusters) == 1
    assert clusters[0]["DBClusterIdentifier"] == "cluster-id"
    assert clusters[0]["Engine"] == "neptune"


@mock_neptune
def test_delete_db_cluster():
    client = boto3.client("neptune", region_name="ap-southeast-1")

    client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")
    client.delete_db_cluster(DBClusterIdentifier="cluster-id")

    assert client.describe_db_clusters()["DBClusters"] == []


@mock_neptune
def test_delete_unknown_db_cluster():
    client = boto3.client("neptune", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier="unknown-id")
    err = exc.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"


@mock_neptune
def test_modify_db_cluster():
    client = boto3.client("neptune", region_name="us-east-1")
    client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")
    resp = client.modify_db_cluster(
        DBClusterIdentifier="cluster-id",
        EngineVersion="1.1.0.1",
        DBClusterParameterGroupName="myprm",
        PreferredBackupWindow="window",
    )["DBCluster"]
    assert resp["DBClusterParameterGroup"] == "myprm"
    assert resp["EngineVersion"] == "1.1.0.1"
    assert resp["PreferredBackupWindow"] == "window"


@mock_neptune
def test_start_db_cluster():
    client = boto3.client("neptune", region_name="us-east-2")
    client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")[
        "DBCluster"
    ]

    cluster = client.start_db_cluster(DBClusterIdentifier="cluster-id")["DBCluster"]
    assert cluster["Status"] == "started"
