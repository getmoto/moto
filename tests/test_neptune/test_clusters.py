"""Unit tests for neptune-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
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
    resp.should.have.key("DBClusterIdentifier").equals("cluster-id")
    resp.should.have.key("DbClusterResourceId")
    resp.should.have.key("DBClusterArn")
    resp.should.have.key("Engine").equals("neptune")
    resp.should.have.key("EngineVersion").equals("1.2.0.2")
    resp.should.have.key("StorageEncrypted").equals(True)
    resp.should.have.key("DBClusterParameterGroup").equals("")
    resp.should.have.key("Endpoint")
    resp.should.have.key("DbClusterResourceId").match("cluster-")
    resp.should.have.key("AvailabilityZones").equals(
        ["us-east-2a", "us-east-2b", "us-east-2c"]
    )
    resp.shouldnt.have.key("ServerlessV2ScalingConfiguration")

    # Double check this cluster is not available in another region
    europe_client = boto3.client("neptune", region_name="eu-west-2")
    europe_client.describe_db_clusters()["DBClusters"].should.have.length_of(0)


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
    resp.should.have.key("StorageEncrypted").equals(False)
    resp.should.have.key("DBClusterParameterGroup").equals("myprm")
    resp.should.have.key("EngineVersion").equals("1.1.0.1")
    resp.should.have.key("KmsKeyId").equals("key")
    resp.should.have.key("ServerlessV2ScalingConfiguration").equals(
        {"MinCapacity": 1.0, "MaxCapacity": 2.0}
    )
    resp.should.have.key("DatabaseName").equals("sth")


@mock_neptune
def test_describe_db_clusters():
    client = boto3.client("neptune", region_name="ap-southeast-1")
    client.describe_db_clusters()["DBClusters"].should.equal([])

    client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")

    clusters = client.describe_db_clusters()["DBClusters"]
    clusters.should.have.length_of(1)
    clusters[0]["DBClusterIdentifier"].should.equal("cluster-id")
    clusters[0].should.have.key("Engine").equals("neptune")


@mock_neptune
def test_delete_db_cluster():
    client = boto3.client("neptune", region_name="ap-southeast-1")

    client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")
    client.delete_db_cluster(DBClusterIdentifier="cluster-id")

    client.describe_db_clusters()["DBClusters"].should.equal([])


@mock_neptune
def test_delete_unknown_db_cluster():
    client = boto3.client("neptune", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier="unknown-id")
    err = exc.value.response["Error"]
    err["Code"].should.equal("DBClusterNotFoundFault")


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
    resp.should.have.key("DBClusterParameterGroup").equals("myprm")
    resp.should.have.key("EngineVersion").equals("1.1.0.1")
    resp.should.have.key("PreferredBackupWindow").equals("window")


@mock_neptune
def test_start_db_cluster():
    client = boto3.client("neptune", region_name="us-east-2")
    client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="neptune")[
        "DBCluster"
    ]

    cluster = client.start_db_cluster(DBClusterIdentifier="cluster-id")["DBCluster"]
    cluster.should.have.key("Status").equals("started")
