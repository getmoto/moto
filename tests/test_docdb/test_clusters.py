import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_db_cluster():
    client = boto3.client("docdb", region_name="us-east-2")
    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )["DBCluster"]
    assert resp["DBClusterIdentifier"] == "cluster-id"
    assert "DbClusterResourceId" in resp
    assert "DBClusterArn" in resp
    assert resp["Engine"] == "docdb"
    assert resp["EngineVersion"] == "5.0.0"
    assert resp["Port"] == 27017
    assert resp["MasterUsername"] == "root"
    assert resp["StorageEncrypted"] is False
    assert resp["DBClusterParameterGroup"] == "default.docdb5.0"
    assert "Endpoint" in resp
    assert "ReaderEndpoint" in resp
    assert "cluster-" in resp["DbClusterResourceId"]
    assert resp["AvailabilityZones"] == ["us-east-2a", "us-east-2b", "us-east-2c"]
    assert resp["DBClusterMembers"] == []

    # Double check this cluster is not available in another region
    europe_client = boto3.client("docdb", region_name="eu-west-2")
    assert len(europe_client.describe_db_clusters()["DBClusters"]) == 0


@mock_aws
def test_create_db_cluster__with_additional_params():
    client = boto3.client("docdb", region_name="us-east-1")
    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        EngineVersion="4.0.0",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        Port=27018,
        StorageEncrypted=True,
        DBClusterParameterGroupName="myprm",
        KmsKeyId="key",
        DeletionProtection=True,
        BackupRetentionPeriod=7,
        PreferredBackupWindow="01:00-02:00",
        PreferredMaintenanceWindow="sun:03:00-sun:04:00",
        EnableCloudwatchLogsExports=["audit", "profiler"],
    )["DBCluster"]
    assert resp["EngineVersion"] == "4.0.0"
    assert resp["Port"] == 27018
    assert resp["StorageEncrypted"] is True
    assert resp["DBClusterParameterGroup"] == "myprm"
    assert resp["KmsKeyId"] == "key"
    assert resp["DeletionProtection"] is True
    assert resp["BackupRetentionPeriod"] == 7
    assert resp["PreferredBackupWindow"] == "01:00-02:00"
    assert resp["PreferredMaintenanceWindow"] == "sun:03:00-sun:04:00"
    assert resp["EnabledCloudwatchLogsExports"] == ["audit", "profiler"]


@mock_aws
def test_create_db_cluster__without_master_username():
    client = boto3.client("docdb", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_db_cluster(DBClusterIdentifier="cluster-id", Engine="docdb")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert "MasterUsername" in err["Message"]


@mock_aws
def test_create_db_cluster__unknown_engine():
    client = boto3.client("docdb", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id",
            Engine="mongodb",
            MasterUsername="root",
            MasterUserPassword="hunter2000",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"


@mock_aws
def test_create_db_cluster_with_instance():
    client = boto3.client("docdb", region_name="us-east-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    resp = client.create_db_instance(
        DBInstanceIdentifier="instance-id",
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        DBInstanceClass="db.r5.large",
    )["DBInstance"]
    assert resp["DBInstanceIdentifier"] == "instance-id"
    assert resp["Engine"] == "docdb"

    resp = client.describe_db_instances(DBInstanceIdentifier="instance-id")[
        "DBInstances"
    ]
    assert resp[0]["DBInstanceIdentifier"] == "instance-id"
    assert resp[0]["DBInstanceClass"] == "db.r5.large"
    assert resp[0]["DBClusterIdentifier"] == "cluster-id"
    assert resp[0]["Engine"] == "docdb"
    assert resp[0]["EngineVersion"] == "5.0.0"
    assert resp[0]["Endpoint"]["Port"] == 27017

    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-id")[
        "DBClusters"
    ][0]
    assert len(cluster["DBClusterMembers"]) == 1
    assert cluster["DBClusterMembers"][0]["DBInstanceIdentifier"] == "instance-id"
    assert cluster["DBClusterMembers"][0]["IsClusterWriter"] is True


@mock_aws
def test_describe_db_clusters():
    client = boto3.client("docdb", region_name="ap-southeast-1")
    assert client.describe_db_clusters()["DBClusters"] == []

    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )

    clusters = client.describe_db_clusters(DBClusterIdentifier="cluster-id")[
        "DBClusters"
    ]
    assert len(clusters) == 1
    assert clusters[0]["DBClusterIdentifier"] == "cluster-id"
    assert clusters[0]["Engine"] == "docdb"
    assert clusters[0]["Status"] == "available"


@mock_aws
def test_describe_db_clusters__filter_by_engine():
    client = boto3.client("docdb", region_name="us-east-1")
    client.create_db_cluster(
        DBClusterIdentifier="docdb-cluster",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    # Clusters are shared with the RDS backend, just like in AWS
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_cluster(
        DBClusterIdentifier="aurora-cluster",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    assert len(client.describe_db_clusters()["DBClusters"]) == 2

    clusters = client.describe_db_clusters(
        Filters=[{"Name": "engine", "Values": ["docdb"]}]
    )["DBClusters"]
    assert [c["DBClusterIdentifier"] for c in clusters] == ["docdb-cluster"]


@mock_aws
def test_describe_unknown_db_cluster():
    client = boto3.client("docdb", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.describe_db_clusters(DBClusterIdentifier="unknown-id")
    err = exc.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"


@mock_aws
def test_delete_db_cluster():
    client = boto3.client("docdb", region_name="ap-southeast-1")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    resp = client.delete_db_cluster(DBClusterIdentifier="cluster-id")["DBCluster"]
    assert resp["DBClusterIdentifier"] == "cluster-id"

    assert client.describe_db_clusters()["DBClusters"] == []


@mock_aws
def test_delete_db_cluster__with_deletion_protection():
    client = boto3.client("docdb", region_name="ap-southeast-1")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
        DeletionProtection=True,
    )
    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier="cluster-id")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"

    client.modify_db_cluster(DBClusterIdentifier="cluster-id", DeletionProtection=False)
    client.delete_db_cluster(DBClusterIdentifier="cluster-id")
    assert client.describe_db_clusters()["DBClusters"] == []


@mock_aws
def test_remove_db_instance():
    client = boto3.client("docdb", region_name="us-east-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    client.create_db_instance(
        DBInstanceIdentifier="instance-id",
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        DBInstanceClass="db.r5.large",
    )

    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert len(cluster["DBClusterMembers"]) == 1

    client.delete_db_instance(DBInstanceIdentifier="instance-id")

    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert cluster["DBClusterMembers"] == []
    assert client.describe_db_instances()["DBInstances"] == []


@mock_aws
def test_delete_unknown_db_cluster():
    client = boto3.client("docdb", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier="unknown-id")
    err = exc.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"


@mock_aws
def test_modify_db_cluster():
    client = boto3.client("docdb", region_name="us-east-1")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    resp = client.modify_db_cluster(
        DBClusterIdentifier="cluster-id",
        EngineVersion="4.0.0",
        DBClusterParameterGroupName="myprm",
        PreferredBackupWindow="window",
        BackupRetentionPeriod=5,
        DeletionProtection=True,
    )["DBCluster"]
    assert resp["DBClusterParameterGroup"] == "myprm"
    assert resp["EngineVersion"] == "4.0.0"
    assert resp["PreferredBackupWindow"] == "window"
    assert resp["BackupRetentionPeriod"] == 5
    assert resp["DeletionProtection"] is True

    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-id")[
        "DBClusters"
    ][0]
    assert cluster["EngineVersion"] == "4.0.0"
    assert cluster["DeletionProtection"] is True


@mock_aws
def test_stop_and_start_db_cluster():
    client = boto3.client("docdb", region_name="us-east-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    cluster = client.stop_db_cluster(DBClusterIdentifier="cluster-id")["DBCluster"]
    assert cluster["DBClusterIdentifier"] == "cluster-id"

    cluster = client.start_db_cluster(DBClusterIdentifier="cluster-id")["DBCluster"]
    assert cluster["Status"] == "started"


@mock_aws
def test_failover_db_cluster():
    client = boto3.client("docdb", region_name="us-east-2")
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="docdb",
        MasterUsername="root",
        MasterUserPassword="hunter2000",
    )
    for name in ["instance-1", "instance-2"]:
        client.create_db_instance(
            DBInstanceIdentifier=name,
            DBClusterIdentifier="cluster-id",
            Engine="docdb",
            DBInstanceClass="db.r5.large",
        )
    members = client.describe_db_clusters()["DBClusters"][0]["DBClusterMembers"]
    writers = {m["DBInstanceIdentifier"]: m["IsClusterWriter"] for m in members}
    assert writers == {"instance-1": True, "instance-2": False}

    client.failover_db_cluster(
        DBClusterIdentifier="cluster-id", TargetDBInstanceIdentifier="instance-2"
    )
    members = client.describe_db_clusters()["DBClusters"][0]["DBClusterMembers"]
    writers = {m["DBInstanceIdentifier"]: m["IsClusterWriter"] for m in members}
    assert writers == {"instance-1": False, "instance-2": True}
