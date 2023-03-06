import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_neptune


@mock_neptune
def test_describe():
    client = boto3.client("neptune", "us-east-2")
    client.describe_global_clusters()["GlobalClusters"].should.equal([])


@mock_neptune
def test_create_global_cluster():
    client = boto3.client("neptune", "us-east-1")
    resp = client.create_global_cluster(GlobalClusterIdentifier="g-id")["GlobalCluster"]
    resp.should.have.key("GlobalClusterIdentifier").equals("g-id")
    resp.should.have.key("GlobalClusterResourceId")
    resp.should.have.key("GlobalClusterArn")
    resp.should.have.key("Engine").equals("neptune")
    resp.should.have.key("EngineVersion").equals("1.2.0.0")
    resp.should.have.key("StorageEncrypted").equals(False)
    resp.should.have.key("DeletionProtection").equals(False)

    client.describe_global_clusters()["GlobalClusters"].should.have.length_of(1)

    # As a global cluster, verify it can be retrieved everywhere
    europe_client = boto3.client("neptune", "eu-north-1")
    europe_client.describe_global_clusters()["GlobalClusters"].should.have.length_of(1)


@mock_neptune
def test_create_global_cluster_with_additional_params():
    client = boto3.client("neptune", "us-east-1")
    resp = client.create_global_cluster(
        GlobalClusterIdentifier="g-id",
        EngineVersion="1.0",
        DeletionProtection=True,
        StorageEncrypted=True,
    )["GlobalCluster"]
    resp.should.have.key("Engine").equals("neptune")
    resp.should.have.key("EngineVersion").equals("1.0")
    resp.should.have.key("StorageEncrypted").equals(True)
    resp.should.have.key("DeletionProtection").equals(True)


@mock_neptune
def test_delete_global_cluster():
    client = boto3.client("neptune", "us-east-1")
    client.create_global_cluster(GlobalClusterIdentifier="g-id2")

    client.delete_global_cluster(GlobalClusterIdentifier="g-id2")

    client.describe_global_clusters()["GlobalClusters"].should.equal([])
