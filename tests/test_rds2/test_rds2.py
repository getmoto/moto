import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from moto import mock_rds2
from moto.core import ACCOUNT_ID


def test_deprecation_warning():
    with pytest.warns(None) as record:
        mock_rds2()
    str(record[0].message).should.contain(
        "Module mock_rds2 has been deprecated, and will be removed in a later release."
    )
    str(record[0].message).should.contain("Please use mock_rds instead.")


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
    cluster.should.have.key("DBClusterParameterGroup").equal("default.aurora8.0")
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
