import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_rds


@mock_rds
def test_add_instance_as_cluster_member():
    # When creating a rds instance with DBClusterIdentifier provided,
    # the instance is included as a ClusterMember in the describe_db_clusters call
    client = boto3.client("rds", "us-east-1")

    _ = client.create_db_cluster(
        DBClusterIdentifier="dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]
    client.create_db_instance(
        DBInstanceIdentifier="dbi",
        DBClusterIdentifier="dbci",
        DBInstanceClass="db.r5.large",
        Engine="aurora-postgresql",
    )

    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert "DBClusterMembers" in cluster

    members = cluster["DBClusterMembers"]
    assert len(members) == 1
    assert members[0] == {
        "DBInstanceIdentifier": "dbi",
        "IsClusterWriter": True,
        "DBClusterParameterGroupStatus": "in-sync",
        "PromotionTier": 1,
    }


@mock_rds
def test_remove_instance_from_cluster():
    # When creating a rds instance with DBClusterIdentifier provided,
    # the instance is included as a ClusterMember in the describe_db_clusters call
    client = boto3.client("rds", "us-east-1")

    _ = client.create_db_cluster(
        DBClusterIdentifier="dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]
    client.create_db_instance(
        DBInstanceIdentifier="dbi",
        DBClusterIdentifier="dbci",
        DBInstanceClass="db.r5.large",
        Engine="aurora-postgresql",
    )

    client.delete_db_instance(
        DBInstanceIdentifier="dbi",
        SkipFinalSnapshot=True,
    )

    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert "DBClusterMembers" in cluster

    members = cluster["DBClusterMembers"]
    assert len(members) == 0


@mock_rds
def test_add_instance_to_serverless_cluster():
    client = boto3.client("rds", "us-east-1")

    _ = client.create_db_cluster(
        DBClusterIdentifier="dbci",
        Engine="aurora",
        EngineMode="serverless",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]
    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            DBInstanceIdentifier="dbi",
            DBClusterIdentifier="dbci",
            DBInstanceClass="db.r5.large",
            Engine="aurora-postgresql",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Instances cannot be added to Aurora Serverless clusters."
