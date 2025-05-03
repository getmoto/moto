import re

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

from . import DEFAULT_REGION
from .test_rds import create_db_instance

test_tags = [
    {
        "Key": "foo",
        "Value": "bar",
    },
    {
        "Key": "foo1",
        "Value": "bar1",
    },
]


@pytest.fixture(name="client")
@mock_aws
def get_rds_client():
    return boto3.client("rds", region_name=DEFAULT_REGION)


def create_db_cluster(**extra_kwargs) -> str:
    client = boto3.client("rds", region_name=DEFAULT_REGION)
    default_kwargs = {
        "DBClusterIdentifier": "db-primary-1",
        "AllocatedStorage": 10,
        "Engine": "postgres",
        "DatabaseName": "staging-postgres",
        "DBClusterInstanceClass": "db.m1.small",
        "MasterUsername": "root",
        "MasterUserPassword": "hunter2000",
        "Port": 1234,
    }
    default_kwargs.update(extra_kwargs)
    client.create_db_cluster(**default_kwargs)
    return default_kwargs["DBClusterIdentifier"]


@mock_aws
def test_describe_db_cluster_initial(client):
    resp = client.describe_db_clusters()
    assert len(resp["DBClusters"]) == 0


@mock_aws
def test_describe_db_cluster_fails_for_non_existent_cluster(client):
    resp = client.describe_db_clusters()
    assert len(resp["DBClusters"]) == 0
    with pytest.raises(ClientError) as ex:
        client.describe_db_clusters(DBClusterIdentifier="cluster-id")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-id not found."


@mock_aws
def test_create_db_cluster_invalid_engine(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id", Engine="aurora-postgresql"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUsername must be provided and must not be blank."
    )


@mock_aws
def test_create_db_cluster_needs_master_username(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id", Engine="aurora-postgresql"
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUsername must be provided and must not be blank."
    )


@mock_aws
def test_create_db_cluster_needs_master_user_password(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            DBClusterIdentifier="cluster-id",
            Engine="aurora-postgresql",
            MasterUsername="root",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUserPassword must be provided and must not be blank."
    )


@mock_aws
def test_create_db_cluster_needs_long_master_user_password(client):
    with pytest.raises(ClientError) as ex:
        create_db_cluster(
            MasterUserPassword="hunter2",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUserPassword is not a valid password because "
        "it is shorter than 8 characters."
    )


@mock_aws
def test_modify_db_cluster_needs_long_master_user_password(client):
    db_cluster_identifier = create_db_cluster()

    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster(
            DBClusterIdentifier=db_cluster_identifier,
            MasterUserPassword="hunter2",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter MasterUserPassword is not a valid password because "
        "it is shorter than 8 characters."
    )


@mock_aws
def test_modify_db_cluster_new_cluster_identifier(client):
    old_id = create_db_cluster()
    new_id = "new-cluster-id"

    resp = client.modify_db_cluster(
        DBClusterIdentifier=old_id,
        NewDBClusterIdentifier=new_id,
    )

    assert resp["DBCluster"]["DBClusterIdentifier"] == new_id

    clusters = [
        cluster["DBClusterIdentifier"]
        for cluster in client.describe_db_clusters()["DBClusters"]
    ]

    assert old_id not in clusters


@pytest.mark.parametrize("with_custom_kms_key", [True, False])
@mock_aws
def test_modify_db_cluster_manage_master_user_password(client, with_custom_kms_key):
    cluster_id = "cluster-id"
    kms = boto3.client("kms", region_name=DEFAULT_REGION)
    key = kms.create_key(KeyUsage="ENCRYPT_DECRYPT", KeySpec="SYMMETRIC_DEFAULT")[
        "KeyMetadata"
    ]
    custom_kms_key = key["Arn"]
    custom_kms_key_args = (
        {"MasterUserSecretKmsKeyId": custom_kms_key} if with_custom_kms_key else {}
    )

    create_response = client.create_db_cluster(
        DBClusterIdentifier=cluster_id,
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter21",
        ManageMasterUserPassword=False,
    )

    modify_response = client.modify_db_cluster(
        DBClusterIdentifier=cluster_id,
        ManageMasterUserPassword=True,
        **custom_kms_key_args,
    )

    describe_response = client.describe_db_clusters(
        DBClusterIdentifier=cluster_id,
    )

    revert_modification_response = client.modify_db_cluster(
        DBClusterIdentifier=cluster_id, ManageMasterUserPassword=False
    )

    retry_revert_modification_response = client.modify_db_cluster(
        DBClusterIdentifier=cluster_id, ManageMasterUserPassword=False
    )

    assert create_response["DBCluster"].get("MasterUserSecret") is None
    master_user_secret = modify_response["DBCluster"]["MasterUserSecret"]
    assert len(master_user_secret.keys()) == 3
    assert str(master_user_secret["SecretArn"]).startswith(
        f"arn:aws:secretsmanager:{DEFAULT_REGION}:{ACCOUNT_ID}:secret:rds!cluster"
    )
    assert master_user_secret["SecretStatus"] == "creating"
    if with_custom_kms_key:
        assert master_user_secret["KmsKeyId"] == custom_kms_key
    else:
        default_kms_key = kms.describe_key(KeyId="alias/aws/secretsmanager")[
            "KeyMetadata"
        ]["Arn"]
        assert master_user_secret["KmsKeyId"] == default_kms_key
    assert len(describe_response["DBClusters"][0]["MasterUserSecret"].keys()) == 3
    assert (
        describe_response["DBClusters"][0]["MasterUserSecret"]["SecretStatus"]
        == "active"
    )
    assert (
        modify_response["DBCluster"]["MasterUserSecret"]["SecretArn"]
        == describe_response["DBClusters"][0]["MasterUserSecret"]["SecretArn"]
    )
    assert revert_modification_response["DBCluster"].get("MasterUserSecret") is None
    assert (
        retry_revert_modification_response["DBCluster"].get("MasterUserSecret") is None
    )


@pytest.mark.parametrize("with_apply_immediately", [True, False])
@mock_aws
def test_modify_db_cluster_rotate_master_user_password(client, with_apply_immediately):
    db_cluster_identifier = create_db_cluster(ManageMasterUserPassword=True)

    if with_apply_immediately:
        modify_response = client.modify_db_cluster(
            DBClusterIdentifier=db_cluster_identifier,
            RotateMasterUserPassword=True,
            ApplyImmediately=True,
        )

        describe_response = client.describe_db_clusters(
            DBClusterIdentifier=db_cluster_identifier,
        )

        assert (
            modify_response["DBCluster"]["MasterUserSecret"]["SecretStatus"]
            == "rotating"
        )
        assert (
            describe_response["DBClusters"][0]["MasterUserSecret"]["SecretStatus"]
            == "active"
        )

    else:
        with pytest.raises(ClientError):
            client.modify_db_cluster(
                DBClusterIdentifier=db_cluster_identifier,
                RotateMasterUserPassword=True,
            )


@mock_aws
def test_create_db_cluster__verify_default_properties(client):
    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-mysql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )
    assert "DBCluster" in resp

    cluster = resp["DBCluster"]

    # This was not supplied, so should not be returned
    assert "DatabaseName" not in cluster

    assert "AvailabilityZones" in cluster
    assert set(cluster["AvailabilityZones"]) == {
        "us-west-2a",
        "us-west-2b",
        "us-west-2c",
    }
    assert cluster["BackupRetentionPeriod"] == 1
    assert cluster["DBClusterIdentifier"] == "cluster-id"
    assert cluster["DBClusterParameterGroup"] == "default.aurora8.0"
    assert cluster["DBSubnetGroup"] == "default"
    assert cluster["Status"] == "creating"
    assert re.match(
        "cluster-id.cluster-[a-z0-9]{12}.us-west-2.rds.amazonaws.com",
        cluster["Endpoint"],
    )
    endpoint = cluster["Endpoint"]
    expected_readonly = endpoint.replace(
        "cluster-id.cluster-", "cluster-id.cluster-ro-"
    )
    assert cluster["ReaderEndpoint"] == expected_readonly
    assert cluster["MultiAZ"] is False
    assert cluster["Engine"] == "aurora-mysql"
    assert cluster["EngineVersion"] == "5.7.mysql_aurora.2.07.2"
    assert cluster["Port"] == 3306
    assert cluster["MasterUsername"] == "root"
    assert cluster["PreferredBackupWindow"] == "01:37-02:07"
    assert cluster["PreferredMaintenanceWindow"] == "wed:02:40-wed:03:10"
    assert cluster["ReadReplicaIdentifiers"] == []
    assert cluster["DBClusterMembers"] == []
    assert "VpcSecurityGroups" in cluster
    assert "HostedZoneId" in cluster
    assert cluster["StorageEncrypted"] is False
    assert re.match(r"cluster-[A-Z0-9]{26}", cluster["DbClusterResourceId"])
    assert cluster["DBClusterArn"] == (
        f"arn:aws:rds:{DEFAULT_REGION}:{ACCOUNT_ID}:cluster:cluster-id"
    )
    assert cluster["AssociatedRoles"] == []
    assert cluster["IAMDatabaseAuthenticationEnabled"] is False
    assert cluster["EngineMode"] == "provisioned"
    assert cluster["DeletionProtection"] is False
    assert cluster["HttpEndpointEnabled"] is False
    assert cluster["CopyTagsToSnapshot"] is False
    assert cluster["CrossAccountClone"] is False
    assert cluster["DeletionProtection"] is False
    assert cluster["DomainMemberships"] == []
    assert cluster["TagList"] == []
    assert "ClusterCreateTime" in cluster
    assert cluster["EarliestRestorableTime"] >= cluster["ClusterCreateTime"]
    assert cluster["StorageEncrypted"] is False
    assert cluster["GlobalWriteForwardingRequested"] is False


@mock_aws
def test_create_db_cluster_additional_parameters(client):
    resp = client.create_db_cluster(
        AvailabilityZones=["eu-north-1b"],
        DatabaseName="users",
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        EngineVersion="8.0.mysql_aurora.3.01.0",
        EngineMode="serverless",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        Port=1234,
        DeletionProtection=True,
        EnableCloudwatchLogsExports=["audit"],
        KmsKeyId="some:kms:arn",
        NetworkType="IPV4",
        DBSubnetGroupName="subnetgroupname",
        StorageEncrypted=True,
        EnableGlobalWriteForwarding=True,
        ScalingConfiguration={
            "MinCapacity": 5,
            "AutoPause": True,
        },
        ServerlessV2ScalingConfiguration={
            "MinCapacity": 2,
            "MaxCapacity": 4,
        },
        VpcSecurityGroupIds=["sg1", "sg2"],
        EnableIAMDatabaseAuthentication=True,
        AutoMinorVersionUpgrade=False,
    )

    cluster = resp["DBCluster"]

    assert cluster["AutoMinorVersionUpgrade"] is False
    assert cluster["DBClusterIdentifier"] == "cluster-id"
    assert cluster["AvailabilityZones"] == ["eu-north-1b"]
    assert cluster["DatabaseName"] == "users"
    assert cluster["Engine"] == "aurora-postgresql"
    assert cluster["EngineVersion"] == "8.0.mysql_aurora.3.01.0"
    assert cluster["EngineMode"] == "serverless"
    assert cluster["Port"] == 1234
    assert cluster["DeletionProtection"] is True
    assert cluster["EnabledCloudwatchLogsExports"] == ["audit"]
    assert cluster["KmsKeyId"] == "some:kms:arn"
    assert cluster["NetworkType"] == "IPV4"
    assert cluster["DBSubnetGroup"] == "subnetgroupname"
    assert cluster["StorageEncrypted"] is True
    assert cluster["GlobalWriteForwardingRequested"] is True
    assert cluster["ScalingConfigurationInfo"] == {"MinCapacity": 5, "AutoPause": True}
    assert cluster["ServerlessV2ScalingConfiguration"] == {
        "MaxCapacity": 4.0,
        "MinCapacity": 2.0,
    }

    security_groups = cluster["VpcSecurityGroups"]
    assert len(security_groups) == 2
    assert {"VpcSecurityGroupId": "sg1", "Status": "active"} in security_groups
    assert {"VpcSecurityGroupId": "sg2", "Status": "active"} in security_groups
    assert cluster["IAMDatabaseAuthenticationEnabled"] is True


@mock_aws
def test_modify_db_cluster_serverless_v2_scaling_configuration(client):
    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        EngineMode="serverless",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        ServerlessV2ScalingConfiguration={
            "MinCapacity": 2,
            "MaxCapacity": 4,
        },
    )
    cluster = resp["DBCluster"]
    assert cluster["Engine"] == "aurora-postgresql"
    assert cluster["EngineMode"] == "serverless"
    assert cluster["ServerlessV2ScalingConfiguration"] == {
        "MaxCapacity": 4.0,
        "MinCapacity": 2.0,
    }
    client.modify_db_cluster(
        DBClusterIdentifier="cluster-id",
        ServerlessV2ScalingConfiguration={
            "MinCapacity": 4,
            "MaxCapacity": 8,
        },
    )
    resp = client.describe_db_clusters(DBClusterIdentifier="cluster-id")
    cluster_modified = resp["DBClusters"][0]
    assert cluster_modified["Engine"] == "aurora-postgresql"
    assert cluster_modified["EngineMode"] == "serverless"
    assert cluster_modified["ServerlessV2ScalingConfiguration"] == {
        "MaxCapacity": 8.0,
        "MinCapacity": 4.0,
    }


@pytest.mark.parametrize(
    "attr_info",
    [
        ("BackupRetentionPeriod", 15, 32),
        ("EngineVersion", "9.6", "10.2"),
    ],
    ids=[
        "BackupRetentionPeriod",
        "EngineVersion",
    ],
)
@mock_aws
def test_db_instance_in_cluster_gets_attributes_from_cluster(client, attr_info):
    attribute, initial_value, modified_value = attr_info
    cluster = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="<PASSWORD>",
        **{attribute: initial_value},
    )["DBCluster"]
    instance = create_db_instance(
        DBInstanceIdentifier="clustered-instance",
        DBClusterIdentifier=cluster["DBClusterIdentifier"],
        Engine="aurora-postgresql",
    )
    assert instance["AllocatedStorage"] == cluster["AllocatedStorage"]
    assert instance["MasterUsername"] == cluster["MasterUsername"]
    assert instance["PreferredBackupWindow"] == cluster["PreferredBackupWindow"]
    assert instance["StorageEncrypted"] == cluster["StorageEncrypted"]
    assert instance[attribute] == cluster[attribute] == initial_value
    cluster = client.modify_db_cluster(
        DBClusterIdentifier=cluster["DBClusterIdentifier"],
        ApplyImmediately=True,
        **{attribute: modified_value},
    )["DBCluster"]
    instance = client.describe_db_instances(
        DBInstanceIdentifier=instance["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert instance[attribute] == cluster[attribute] == modified_value


@mock_aws
def test_describe_db_cluster_after_creation(client):
    client.create_db_cluster(
        DBClusterIdentifier="cluster-id1",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )

    cluster_arn = client.create_db_cluster(
        DBClusterIdentifier="cluster-id2",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
    )["DBCluster"]["DBClusterArn"]

    assert len(client.describe_db_clusters()["DBClusters"]) == 2

    assert (
        len(
            client.describe_db_clusters(DBClusterIdentifier="cluster-id2")["DBClusters"]
        )
        == 1
    )

    assert (
        len(client.describe_db_clusters(DBClusterIdentifier=cluster_arn)["DBClusters"])
        == 1
    )


@mock_aws
def test_delete_db_cluster(client):
    db_cluster_identifier = create_db_cluster()
    client.delete_db_cluster(DBClusterIdentifier=db_cluster_identifier)
    assert len(client.describe_db_clusters()["DBClusters"]) == 0


@mock_aws
def test_delete_db_cluster_do_snapshot(client):
    db_cluster_identifier = create_db_cluster()
    client.delete_db_cluster(
        DBClusterIdentifier=db_cluster_identifier,
        FinalDBSnapshotIdentifier="final-snapshot",
    )
    assert len(client.describe_db_clusters()["DBClusters"]) == 0
    snapshot = client.describe_db_cluster_snapshots(
        DBClusterSnapshotIdentifier="final-snapshot"
    )["DBClusterSnapshots"][0]
    assert snapshot["DBClusterIdentifier"] == db_cluster_identifier
    assert snapshot["DBClusterSnapshotIdentifier"] == "final-snapshot"
    assert snapshot["SnapshotType"] == "manual"


@mock_aws
def test_delete_db_cluster_that_is_protected(client):
    db_cluster_identifier = create_db_cluster(DeletionProtection=True)
    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier=db_cluster_identifier)
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "Cannot delete protected Cluster, please disable deletion protection and try again."
    )


@mock_aws
def test_delete_db_cluster_with_instances_deletion_protection_disabled(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-1",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-2",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    assert len(cluster["DBClusterMembers"]) == 2
    client.delete_db_instance(DBInstanceIdentifier="test-instance-1")
    client.delete_db_instance(DBInstanceIdentifier="test-instance-2")
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    assert len(cluster["DBClusterMembers"]) == 0
    cluster = client.delete_db_cluster(DBClusterIdentifier="cluster-1").get("DBCluster")
    assert cluster["DBClusterIdentifier"] == "cluster-1"


@mock_aws
def test_delete_db_cluster_with_instances_deletion_protection_enabled(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
        DeletionProtection=True,
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-1",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-2",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    assert len(cluster["DBClusterMembers"]) == 2
    client.delete_db_instance(DBInstanceIdentifier="test-instance-1")
    client.delete_db_instance(DBInstanceIdentifier="test-instance-2")
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1").get(
        "DBClusters"
    )[0]
    assert len(cluster["DBClusterMembers"]) == 0
    with pytest.raises(ClientError) as exc:
        client.delete_db_cluster(DBClusterIdentifier="cluster-1")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "Cannot delete protected Cluster, please disable deletion protection and try again."
    )


@mock_aws
def test_delete_db_cluster_unknown_cluster(client):
    with pytest.raises(ClientError) as ex:
        client.delete_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-unknown not found."


@mock_aws
def test_start_db_cluster_unknown_cluster(client):
    with pytest.raises(ClientError) as ex:
        client.start_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-unknown not found."


@mock_aws
def test_start_db_cluster_after_stopping(client):
    db_cluster_identifier = create_db_cluster()
    client.stop_db_cluster(DBClusterIdentifier=db_cluster_identifier)

    client.start_db_cluster(DBClusterIdentifier=db_cluster_identifier)
    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert cluster["Status"] == "available"


@mock_aws
def test_start_db_cluster_without_stopping(client):
    db_cluster_identifier = create_db_cluster()

    with pytest.raises(ClientError) as ex:
        client.start_db_cluster(DBClusterIdentifier=db_cluster_identifier)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidDBClusterStateFault"
    assert (
        err["Message"]
        == f"DbCluster {db_cluster_identifier} is in available state but expected it to be one of stopped,inaccessible-encryption-credentials-recoverable."
    )


@mock_aws
def test_stop_db_cluster(client):
    db_cluster_identifier = create_db_cluster()
    resp = client.stop_db_cluster(DBClusterIdentifier=db_cluster_identifier)
    # Quirk of the AWS implementation - the immediate response show it's still available
    cluster = resp["DBCluster"]
    assert cluster["Status"] == "available"
    # For some time the status will be 'stopping'
    # And finally it will be 'stopped'
    cluster = client.describe_db_clusters()["DBClusters"][0]
    assert cluster["Status"] == "stopped"


@mock_aws
def test_stop_db_cluster_already_stopped(client):
    db_cluster_identifier = create_db_cluster()
    client.stop_db_cluster(DBClusterIdentifier=db_cluster_identifier)

    # can't call stop on a stopped cluster
    with pytest.raises(ClientError) as ex:
        client.stop_db_cluster(DBClusterIdentifier=db_cluster_identifier)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidDBClusterStateFault"
    assert (
        err["Message"]
        == f"DbCluster {db_cluster_identifier} is in stopped state but expected it to be one of available."
    )


@mock_aws
def test_stop_db_cluster_unknown_cluster(client):
    with pytest.raises(ClientError) as ex:
        client.stop_db_cluster(DBClusterIdentifier="cluster-unknown")
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    assert err["Message"] == "DBCluster cluster-unknown not found."


@mock_aws
def test_create_db_cluster_snapshot_fails_for_unknown_cluster(client):
    with pytest.raises(ClientError) as exc:
        client.create_db_cluster_snapshot(
            DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-1"
        )
    err = exc.value.response["Error"]
    assert err["Message"] == "DBCluster db-primary-1 not found."


@mock_aws
def test_create_db_cluster_snapshot(client):
    db_cluster_identifier = create_db_cluster()
    snapshot = client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier, DBClusterSnapshotIdentifier="g-1"
    )["DBClusterSnapshot"]

    assert snapshot["Engine"] == "postgres"
    assert snapshot["DBClusterIdentifier"] == "db-primary-1"
    assert snapshot["DBClusterSnapshotIdentifier"] == "g-1"
    assert snapshot["SnapshotType"] == "manual"
    result = client.list_tags_for_resource(
        ResourceName=snapshot["DBClusterSnapshotArn"]
    )
    assert result["TagList"] == []


@mock_aws
def test_create_db_cluster_snapshot_copy_tags(client):
    db_cluster_identifier = create_db_cluster(
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
        CopyTagsToSnapshot=True,
    )

    snapshot = client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier, DBClusterSnapshotIdentifier="g-1"
    )["DBClusterSnapshot"]

    assert snapshot["Engine"] == "postgres"
    assert snapshot["DBClusterIdentifier"] == db_cluster_identifier
    assert snapshot["DBClusterSnapshotIdentifier"] == "g-1"

    result = client.list_tags_for_resource(
        ResourceName=snapshot["DBClusterSnapshotArn"]
    )
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]

    snapshot = client.describe_db_cluster_snapshots(
        DBClusterIdentifier=db_cluster_identifier
    )["DBClusterSnapshots"][0]
    assert snapshot["TagList"] == [
        {"Key": "foo", "Value": "bar"},
        {"Key": "foo1", "Value": "bar1"},
    ]


@mock_aws
def test_copy_db_cluster_snapshot_fails_for_unknown_snapshot(client):
    with pytest.raises(ClientError) as exc:
        client.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="snapshot-1",
            TargetDBClusterSnapshotIdentifier="snapshot-2",
        )

    err = exc.value.response["Error"]
    assert err["Message"] == "DBClusterSnapshot snapshot-1 not found."


@pytest.mark.parametrize("delete_cluster", [True, False])
@mock_aws
def test_copy_db_cluster_snapshot(delete_cluster: bool, client):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )

    if delete_cluster:
        client.delete_db_cluster(DBClusterIdentifier=db_cluster_identifier)

    target_snapshot = client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier="snapshot-1",
        TargetDBClusterSnapshotIdentifier="snapshot-2",
    )["DBClusterSnapshot"]

    assert target_snapshot["Engine"] == "postgres"
    assert target_snapshot["DBClusterIdentifier"] == "db-primary-1"
    assert target_snapshot["DBClusterSnapshotIdentifier"] == "snapshot-2"
    result = client.list_tags_for_resource(
        ResourceName=target_snapshot["DBClusterSnapshotArn"]
    )
    assert result["TagList"] == []


@mock_aws
def test_copy_db_cluster_snapshot_type_is_always_manual(client):
    # Even when copying a snapshot with SnapshotType=="automated", the
    # SnapshotType of the copy is "manual".
    db_cluster_identifier = create_db_cluster()
    client.delete_db_cluster(
        DBClusterIdentifier=db_cluster_identifier,
        FinalDBSnapshotIdentifier="final-snapshot",
    )
    snapshot1 = client.describe_db_cluster_snapshots()["DBClusterSnapshots"][0]
    assert snapshot1["SnapshotType"] == "automated"

    snapshot2 = client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier="final-snapshot",
        TargetDBClusterSnapshotIdentifier="snapshot-2",
    )["DBClusterSnapshot"]
    assert snapshot2["SnapshotType"] == "manual"


@mock_aws
def test_copy_db_cluster_snapshot_fails_for_existed_target_snapshot(client):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )

    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-2",
    )

    with pytest.raises(ClientError) as exc:
        client.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="snapshot-1",
            TargetDBClusterSnapshotIdentifier="snapshot-2",
        )

    err = exc.value.response["Error"]
    assert err["Message"] == (
        "Cannot create the snapshot because a snapshot with the identifier "
        "snapshot-2 already exists."
    )


@mock_aws
def test_create_db_cluster_snapshot_fails_for_existing_snapshot_id(client):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )
    with pytest.raises(ClientError) as exc:
        client.create_db_cluster_snapshot(
            DBClusterIdentifier=db_cluster_identifier,
            DBClusterSnapshotIdentifier="snapshot-1",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DBClusterSnapshotAlreadyExistsFault"
    assert "snapshot-1 already exists." in err["Message"]


@mock_aws
@pytest.mark.skipif(settings.TEST_SERVER_MODE, reason="Cannot set env in server mode")
def test_create_db_cluster_snapshot_fails_when_limit_exceeded(client, monkeypatch):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )
    with pytest.raises(ClientError) as exc:
        monkeypatch.setenv("MOTO_RDS_SNAPSHOT_LIMIT", "1")
        client.create_db_cluster_snapshot(
            DBClusterIdentifier=db_cluster_identifier,
            DBClusterSnapshotIdentifier="snapshot-2",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "SnapshotQuotaExceeded"
    assert (
        err["Message"]
        == "The request cannot be processed because it would exceed the maximum number of snapshots."
    )


@mock_aws
def test_describe_db_cluster_snapshots(client):
    db_cluster_identifier = create_db_cluster()

    created = client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )["DBClusterSnapshot"]

    assert created["Engine"] == "postgres"

    by_database_id = client.describe_db_cluster_snapshots(
        DBClusterIdentifier="db-primary-1",
        SnapshotType="manual",
    )["DBClusterSnapshots"]
    by_snapshot_id = client.describe_db_cluster_snapshots(
        DBClusterSnapshotIdentifier="snapshot-1",
        SnapshotType="manual",
    )["DBClusterSnapshots"]
    assert by_snapshot_id == by_database_id

    snapshot = by_snapshot_id[0]
    assert snapshot == created
    assert snapshot["Engine"] == "postgres"

    client.create_db_cluster_snapshot(
        DBClusterIdentifier="db-primary-1", DBClusterSnapshotIdentifier="snapshot-2"
    )
    snapshots = client.describe_db_cluster_snapshots(
        DBClusterIdentifier="db-primary-1",
        SnapshotType="manual",
    )["DBClusterSnapshots"]
    assert len(snapshots) == 2


@mock_aws
def test_delete_db_cluster_snapshot(client):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )

    client.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier="snapshot-1")
    client.delete_db_cluster_snapshot(DBClusterSnapshotIdentifier="snapshot-1")
    with pytest.raises(ClientError):
        client.describe_db_cluster_snapshots(DBClusterSnapshotIdentifier="snapshot-1")


@mock_aws
def test_restore_db_cluster_from_snapshot(client):
    db_cluster_identifier = create_db_cluster()
    assert len(client.describe_db_clusters()["DBClusters"]) == 1

    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )

    # restore
    new_cluster = client.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="db-restore-1",
        SnapshotIdentifier="snapshot-1",
        Engine="postgres",
    )["DBCluster"]
    assert new_cluster["DBClusterIdentifier"] == "db-restore-1"
    assert new_cluster["DBClusterInstanceClass"] == "db.m1.small"
    assert new_cluster["Engine"] == "postgres"
    assert new_cluster["DatabaseName"] == "staging-postgres"
    assert new_cluster["Port"] == 1234

    # Verify it exists
    assert len(client.describe_db_clusters()["DBClusters"]) == 2
    resp = client.describe_db_clusters(DBClusterIdentifier="db-restore-1")
    assert len(resp["DBClusters"]) == 1


@mock_aws
def test_restore_db_cluster_from_snapshot_and_override_params(client):
    db_cluster_identifier = create_db_cluster()
    assert len(client.describe_db_clusters()["DBClusters"]) == 1
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )

    # restore with some updated attributes
    new_cluster = client.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="db-restore-1",
        SnapshotIdentifier="snapshot-1",
        Engine="postgres",
        Port=10000,
        DBClusterInstanceClass="db.r6g.xlarge",
    )["DBCluster"]
    assert new_cluster["DBClusterIdentifier"] == "db-restore-1"
    assert new_cluster["DBClusterParameterGroup"] == "default.aurora8.0"
    assert new_cluster["DBClusterInstanceClass"] == "db.r6g.xlarge"
    assert new_cluster["Port"] == 10000


@mock_aws
def test_add_tags_to_cluster(client):
    db_cluster_identifier = create_db_cluster(
        Tags=[{"Key": "k1", "Value": "v1"}],
    )
    cluster_arn = (
        f"arn:aws:rds:{DEFAULT_REGION}:123456789012:cluster:{db_cluster_identifier}"
    )

    client.add_tags_to_resource(
        ResourceName=cluster_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = client.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    assert tags == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

    client.remove_tags_from_resource(ResourceName=cluster_arn, TagKeys=["k1"])

    tags = client.list_tags_for_resource(ResourceName=cluster_arn)["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}]


@mock_aws
def test_add_tags_to_cluster_snapshot(client):
    db_cluster_identifier = create_db_cluster(
        Tags=[{"Key": "k1", "Value": "v1"}],
        CopyTagsToSnapshot=True,
    )
    resp = client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier,
        DBClusterSnapshotIdentifier="snapshot-1",
    )
    snapshot_arn = resp["DBClusterSnapshot"]["DBClusterSnapshotArn"]

    client.add_tags_to_resource(
        ResourceName=snapshot_arn, Tags=[{"Key": "k2", "Value": "v2"}]
    )

    tags = client.list_tags_for_resource(ResourceName=snapshot_arn)["TagList"]
    assert tags == [{"Key": "k1", "Value": "v1"}, {"Key": "k2", "Value": "v2"}]

    client.remove_tags_from_resource(ResourceName=snapshot_arn, TagKeys=["k1"])

    tags = client.list_tags_for_resource(ResourceName=snapshot_arn)["TagList"]
    assert tags == [{"Key": "k2", "Value": "v2"}]


@mock_aws
def test_create_serverless_db_cluster(client):
    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        DatabaseName="users",
        Engine="aurora-mysql",
        EngineMode="serverless",
        EngineVersion="5.6.10a",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        EnableHttpEndpoint=True,
    )
    cluster = resp["DBCluster"]
    # This is only true for specific engine versions
    assert cluster["HttpEndpointEnabled"] is True

    # Verify that a default serverless_configuration is added
    assert "ScalingConfigurationInfo" in cluster
    assert cluster["ScalingConfigurationInfo"]["MinCapacity"] == 1
    assert cluster["ScalingConfigurationInfo"]["MaxCapacity"] == 16


@mock_aws
def test_create_db_cluster_with_enable_http_endpoint_invalid(client):
    resp = client.create_db_cluster(
        DBClusterIdentifier="cluster-id",
        DatabaseName="users",
        Engine="aurora-postgresql",
        EngineMode="serverless",
        EngineVersion="5.7.0",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        EnableHttpEndpoint=True,
    )
    cluster = resp["DBCluster"]
    # This attribute is ignored if an invalid engine version is supplied
    assert cluster["HttpEndpointEnabled"] is False


@mock_aws
def test_describe_db_clusters_filter_by_engine(client):
    client.create_db_cluster(
        DBClusterIdentifier="id1",
        Engine="aurora-mysql",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    client.create_db_cluster(
        DBClusterIdentifier="id2",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="hunter21",
    )

    resp = client.describe_db_clusters(
        Filters=[
            {
                "Name": "engine",
                "Values": ["aurora-postgresql"],
            }
        ]
    )

    clusters = resp["DBClusters"]
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["DBClusterIdentifier"] == "id2"
    assert cluster["Engine"] == "aurora-postgresql"


@mock_aws
def test_replicate_cluster():
    # WHEN create_db_cluster is called
    # AND create_db_cluster is called again with ReplicationSourceIdentifier
    #    set to the first cluster
    # THEN promote_read_replica_db_cluster can be called on the second
    #    cluster, elevating it to a read/write cluster
    us_east = boto3.client("rds", "us-east-1")
    us_west = boto3.client("rds", "us-west-1")

    original_arn = us_east.create_db_cluster(
        DBClusterIdentifier="dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
    )["DBCluster"]["DBClusterArn"]

    replica_arn = us_west.create_db_cluster(
        DBClusterIdentifier="replica_dbci",
        Engine="mysql",
        MasterUsername="masterusername",
        MasterUserPassword="hunter2_",
        ReplicationSourceIdentifier=original_arn,
    )["DBCluster"]["DBClusterArn"]

    original = us_east.describe_db_clusters()["DBClusters"][0]
    assert original["ReadReplicaIdentifiers"] == [replica_arn]

    replica = us_west.describe_db_clusters()["DBClusters"][0]
    assert replica["ReplicationSourceIdentifier"] == original_arn
    assert replica["MultiAZ"] is True

    us_west.promote_read_replica_db_cluster(DBClusterIdentifier="replica_dbci")

    original = us_east.describe_db_clusters()["DBClusters"][0]
    assert original["ReadReplicaIdentifiers"] == []

    replica = us_west.describe_db_clusters()["DBClusters"][0]
    assert "ReplicationSourceIdentifier" not in replica
    assert replica["MultiAZ"] is False


@mock_aws
def test_db_cluster_multi_az(client):
    ec2 = boto3.client("ec2", region_name=DEFAULT_REGION)
    resp = ec2.describe_availability_zones()
    zones = [z["ZoneName"] for z in resp["AvailabilityZones"]]
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
    )
    client.create_db_instance(
        DBInstanceIdentifier="test-zone-a",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
        AvailabilityZone=zones[0],
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1")[
        "DBClusters"
    ][0]
    assert cluster["MultiAZ"] is False
    client.create_db_instance(
        DBInstanceIdentifier="test-zone-b",
        DBInstanceClass="db.m1.small",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-1",
        AvailabilityZone=zones[1],
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1")[
        "DBClusters"
    ][0]
    assert cluster["MultiAZ"] is True


@mock_aws
def test_createdb_instance_engine_mismatch_fail(client):
    # Setup
    cluster_name = "test-cluster"
    client.create_db_cluster(
        DBClusterIdentifier=cluster_name,
        Engine="aurora-postgresql",
        EngineVersion="12.14",
        MasterUsername="testuser",
        MasterUserPassword="password",
    )

    # Execute
    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            DBClusterIdentifier=cluster_name,
            Engine="mysql",
            EngineVersion="12.14",
            DBInstanceIdentifier="test-instance",
            DBInstanceClass="db.t4g.medium",
        )

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "The engine name requested for your DB instance (mysql) doesn't match "
        "the engine name of your DB cluster (aurora-postgresql)."
    )


@mock_aws
def test_describe_db_cluster_snapshot_attributes_default(client):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier, DBClusterSnapshotIdentifier="g-1"
    )

    result = client.describe_db_cluster_snapshot_attributes(
        DBClusterSnapshotIdentifier="g-1"
    )["DBClusterSnapshotAttributesResult"]

    assert result["DBClusterSnapshotIdentifier"] == "g-1"
    assert len(result["DBClusterSnapshotAttributes"]) >= 1


@mock_aws
def test_describe_db_cluster_snapshot_attributes(client):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier, DBClusterSnapshotIdentifier="g-1"
    )

    client.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToAdd=["test", "test2"],
    )

    result = client.describe_db_cluster_snapshot_attributes(
        DBClusterSnapshotIdentifier="g-1"
    )["DBClusterSnapshotAttributesResult"]

    assert result["DBClusterSnapshotIdentifier"] == "g-1"
    assert result["DBClusterSnapshotAttributes"][0]["AttributeName"] == "restore"
    assert result["DBClusterSnapshotAttributes"][0]["AttributeValues"] == [
        "test",
        "test2",
    ]


@mock_aws
def test_modify_db_cluster_snapshot_attribute(client):
    db_cluster_identifier = create_db_cluster()
    client.create_db_cluster_snapshot(
        DBClusterIdentifier=db_cluster_identifier, DBClusterSnapshotIdentifier="g-1"
    )

    client.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToAdd=["test", "test2"],
    )
    client.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToRemove=["test"],
    )
    result = client.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier="g-1",
        AttributeName="restore",
        ValuesToAdd=["test3"],
    )["DBClusterSnapshotAttributesResult"]
    assert result["DBClusterSnapshotIdentifier"] == "g-1"
    assert result["DBClusterSnapshotAttributes"][0]["AttributeName"] == "restore"
    assert result["DBClusterSnapshotAttributes"][0]["AttributeValues"] == [
        "test2",
        "test3",
    ]


@mock_aws
def test_backtrack_window(client):
    window = 86400
    resp = client.create_db_cluster(
        AvailabilityZones=["eu-north-1b"],
        DatabaseName="users",
        DBClusterIdentifier="cluster-id",
        Engine="aurora-mysql",
        EngineVersion="8.0.mysql_aurora.3.01.0",
        MasterUsername="root",
        MasterUserPassword="hunter2_",
        Port=1234,
        DeletionProtection=True,
        EnableCloudwatchLogsExports=["audit"],
        NetworkType="IPV4",
        DBSubnetGroupName="subnetgroupname",
        StorageEncrypted=True,
        VpcSecurityGroupIds=["sg1", "sg2"],
        BacktrackWindow=window,
    )

    assert resp["DBCluster"]["BacktrackWindow"] == window


@mock_aws
@pytest.mark.parametrize(
    "params",
    [
        (
            "aurora-mysql",
            -1,
            "The specified value (-1) is not a valid Backtrack Window. Allowed values are within the range of 0 to 259200",
        ),
        (
            "aurora-mysql",
            10000000,
            "The specified value (10000000) is not a valid Backtrack Window. Allowed values are within the range of 0 to 259200",
        ),
        (
            "aurora-postgresql",
            20,
            "Backtrack is not enabled for the postgres engine.",
        ),
    ],
)
def test_backtrack_errors(client, params):
    with pytest.raises(ClientError) as ex:
        client.create_db_cluster(
            AvailabilityZones=["eu-north-1b"],
            DatabaseName="users",
            DBClusterIdentifier="cluster-id",
            Engine=params[0],
            EngineVersion="8.0.mysql_aurora.3.01.0",
            MasterUsername="root",
            MasterUserPassword="hunter2_",
            DBSubnetGroupName="subnetgroupname",
            StorageEncrypted=True,
            VpcSecurityGroupIds=["sg1", "sg2"],
            BacktrackWindow=params[1],
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == params[2]


@mock_aws
def test_describe_and_modify_cluster_snapshot_attributes(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    cluster_snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap", DBClusterIdentifier="cluster-1"
    )["DBClusterSnapshot"]
    assert cluster_snapshot["DBClusterSnapshotIdentifier"] == "cluster-snap"
    cluster_snapshot_attribute_results = client.describe_db_cluster_snapshot_attributes(
        DBClusterSnapshotIdentifier=cluster_snapshot["DBClusterSnapshotIdentifier"]
    )["DBClusterSnapshotAttributesResult"]
    assert (
        cluster_snapshot_attribute_results["DBClusterSnapshotIdentifier"]
        == "cluster-snap"
    )
    assert len(cluster_snapshot_attribute_results["DBClusterSnapshotAttributes"]) == 1
    assert (
        cluster_snapshot_attribute_results["DBClusterSnapshotAttributes"][0][
            "AttributeName"
        ]
        == "restore"
    )
    assert (
        len(
            cluster_snapshot_attribute_results["DBClusterSnapshotAttributes"][0][
                "AttributeValues"
            ]
        )
        == 0
    )

    # Modify the snapshot attribute (Add)
    customer_accounts_add = ["123", "456"]
    cluster_snapshot_attribute_result = client.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier=cluster_snapshot["DBClusterSnapshotIdentifier"],
        AttributeName="restore",
        ValuesToAdd=customer_accounts_add,
    )["DBClusterSnapshotAttributesResult"]
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotIdentifier"]
        == "cluster-snap"
    )
    assert len(cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"]) == 1
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
            "AttributeName"
        ]
        == "restore"
    )
    assert (
        len(
            cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
                "AttributeValues"
            ]
        )
        == 2
    )
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
            "AttributeValues"
        ]
        == customer_accounts_add
    )

    # Modify the snapshot attribute (Add + Remove)
    customer_accounts_add = ["789"]
    customer_accounts_remove = ["123", "456"]
    cluster_snapshot_attribute_result = client.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier=cluster_snapshot["DBClusterSnapshotIdentifier"],
        AttributeName="restore",
        ValuesToAdd=customer_accounts_add,
        ValuesToRemove=customer_accounts_remove,
    )["DBClusterSnapshotAttributesResult"]
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotIdentifier"]
        == "cluster-snap"
    )
    assert len(cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"]) == 1
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
            "AttributeName"
        ]
        == "restore"
    )
    assert (
        len(
            cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
                "AttributeValues"
            ]
        )
        == 1
    )
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
            "AttributeValues"
        ]
        == customer_accounts_add
    )

    # Modify the snapshot attribute (Add + Remove)
    customer_accounts_remove = ["789"]
    cluster_snapshot_attribute_result = client.modify_db_cluster_snapshot_attribute(
        DBClusterSnapshotIdentifier=cluster_snapshot["DBClusterSnapshotIdentifier"],
        AttributeName="restore",
        ValuesToRemove=customer_accounts_remove,
    )["DBClusterSnapshotAttributesResult"]
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotIdentifier"]
        == "cluster-snap"
    )
    assert len(cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"]) == 1
    assert (
        cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
            "AttributeName"
        ]
        == "restore"
    )
    assert (
        len(
            cluster_snapshot_attribute_result["DBClusterSnapshotAttributes"][0][
                "AttributeValues"
            ]
        )
        == 0
    )


@mock_aws
def test_describe_snapshot_attributes_fails_with_invalid_cluster_snapshot_identifier(
    client,
):
    with pytest.raises(ClientError) as ex:
        client.describe_db_cluster_snapshot_attributes(
            DBClusterSnapshotIdentifier="invalid_snapshot_id",
        )
    resp = ex.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert resp["Error"]["Code"] == "DBClusterSnapshotNotFoundFault"


@mock_aws
def test_modify_snapshot_attributes_with_fails_invalid_cluster_snapshot_identifier(
    client,
):
    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster_snapshot_attribute(
            DBClusterSnapshotIdentifier="invalid_snapshot_id",
            AttributeName="restore",
            ValuesToRemove=["123"],
        )
    resp = ex.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert resp["Error"]["Code"] == "DBClusterSnapshotNotFoundFault"


@mock_aws
def test_modify_snapshot_attributes_fails_with_invalid_attribute_name(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    cluster_snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap", DBClusterIdentifier="cluster-1"
    ).get("DBClusterSnapshot")
    assert cluster_snapshot["DBClusterSnapshotIdentifier"] == "cluster-snap"

    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster_snapshot_attribute(
            DBClusterSnapshotIdentifier=cluster_snapshot["DBClusterSnapshotIdentifier"],
            AttributeName="invalid_name",
            ValuesToAdd=["123"],
        )
    resp = ex.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert resp["Error"]["Code"] == "InvalidParameterValue"


@mock_aws
def test_modify_snapshot_attributes_with_fails_invalid_parameter_combination(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    cluster_snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap", DBClusterIdentifier="cluster-1"
    ).get("DBClusterSnapshot")
    assert cluster_snapshot["DBClusterSnapshotIdentifier"] == "cluster-snap"

    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster_snapshot_attribute(
            DBClusterSnapshotIdentifier=cluster_snapshot["DBClusterSnapshotIdentifier"],
            AttributeName="restore",
            ValuesToAdd=["123", "456"],
            ValuesToRemove=["456"],
        )
    resp = ex.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert resp["Error"]["Code"] == "InvalidParameterCombination"


@mock_aws
def test_modify_snapshot_attributes_fails_when_exceeding_number_of_shared_accounts(
    client,
):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    cluster_snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap", DBClusterIdentifier="cluster-1"
    ).get("DBClusterSnapshot")
    assert cluster_snapshot["DBClusterSnapshotIdentifier"] == "cluster-snap"

    customer_accounts_add = [str(x) for x in range(30)]
    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster_snapshot_attribute(
            DBClusterSnapshotIdentifier=cluster_snapshot["DBClusterSnapshotIdentifier"],
            AttributeName="restore",
            ValuesToAdd=customer_accounts_add,
        )
    resp = ex.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert resp["Error"]["Code"] == "SharedSnapshotQuotaExceeded"


@mock_aws
def test_modify_snapshot_attributes_fails_for_automated_snapshot(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    # Automated snapshots
    auto_snapshot = client.describe_db_cluster_snapshots(MaxRecords=20).get(
        "DBClusterSnapshots"
    )[0]
    with pytest.raises(ClientError) as ex:
        client.modify_db_cluster_snapshot_attribute(
            DBClusterSnapshotIdentifier=auto_snapshot["DBClusterSnapshotIdentifier"],
            AttributeName="restore",
        )
    resp = ex.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert resp["Error"]["Code"] == "InvalidDBClusterSnapshotStateFault"


@mock_aws
def test_copy_unencrypted_db_cluster_snapshot_to_encrypted_db_cluster_snapshot(client):
    create_db_cluster(
        DBClusterIdentifier="unencrypted-cluster-1",
        Engine="aurora-postgresql",
        StorageEncrypted=False,
    )
    snapshot = client.create_db_cluster_snapshot(
        DBClusterIdentifier="unencrypted-cluster-1",
        DBClusterSnapshotIdentifier="unencrypted-db-cluster-snapshot",
    )["DBClusterSnapshot"]
    assert snapshot["StorageEncrypted"] is False

    client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier="unencrypted-db-cluster-snapshot",
        TargetDBClusterSnapshotIdentifier="encrypted-db-cluster-snapshot",
        KmsKeyId="alias/aws/rds",
    )
    snapshot = client.describe_db_cluster_snapshots(
        DBClusterSnapshotIdentifier="encrypted-db-cluster-snapshot"
    )["DBClusterSnapshots"][0]
    assert snapshot["Engine"] == "aurora-postgresql"
    assert snapshot["DBClusterSnapshotIdentifier"] == "encrypted-db-cluster-snapshot"
    assert snapshot["StorageEncrypted"] is True


@mock_aws
def test_copy_db_cluster_snapshot_fails_for_existing_target_snapshot(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )

    client.create_db_cluster_snapshot(
        DBClusterIdentifier="cluster-1", DBClusterSnapshotIdentifier="source-snapshot"
    )

    client.create_db_cluster_snapshot(
        DBClusterIdentifier="cluster-1", DBClusterSnapshotIdentifier="target-snapshot"
    )

    with pytest.raises(ClientError) as exc:
        client.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="source-snapshot",
            TargetDBClusterSnapshotIdentifier="target-snapshot",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "DBClusterSnapshotAlreadyExistsFault"
    assert "target-snapshot already exists" in err["Message"]


@mock_aws
@pytest.mark.skipif(settings.TEST_SERVER_MODE, reason="Cannot set env in server mode")
def test_copy_db_cluster_snapshot_fails_when_limit_exceeded(client, monkeypatch):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )

    client.create_db_cluster_snapshot(
        DBClusterIdentifier="cluster-1", DBClusterSnapshotIdentifier="source-snapshot"
    )
    with pytest.raises(ClientError) as exc:
        monkeypatch.setenv("MOTO_RDS_SNAPSHOT_LIMIT", "1")
        client.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="source-snapshot",
            TargetDBClusterSnapshotIdentifier="target-snapshot",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "SnapshotQuotaExceeded"
    assert (
        err["Message"]
        == "The request cannot be processed because it would exceed the maximum number of snapshots."
    )


@mock_aws
def test_create_db_cluster_snapshot_with_tags_overrides_copy_snapshot_tags(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
        CopyTagsToSnapshot=True,
        Tags=test_tags,
    )
    new_snapshot_tags = [
        {
            "Key": "foo",
            "Value": "baz",
        },
    ]
    snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap",
        DBClusterIdentifier="cluster-1",
        Tags=new_snapshot_tags,
    )["DBClusterSnapshot"]
    tag_list = client.list_tags_for_resource(
        ResourceName=snapshot["DBClusterSnapshotArn"]
    )["TagList"]
    assert tag_list == new_snapshot_tags


@mock_aws
def test_copy_db_cluster_snapshot_fails_for_inaccessible_kms_key_arn(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
        StorageEncrypted=True,
    )
    snapshot = client.create_db_cluster_snapshot(
        DBClusterIdentifier="cluster-1", DBClusterSnapshotIdentifier="snapshot-1"
    )["DBClusterSnapshot"]
    assert snapshot["DBClusterSnapshotIdentifier"] == "snapshot-1"

    kms_key_id = (
        "arn:aws:kms:us-east-1:123456789012:key/6e551f00-8a97-4e3b-b620-1a59080bd1be"
    )
    with pytest.raises(ClientError) as ex:
        client.copy_db_cluster_snapshot(
            SourceDBClusterSnapshotIdentifier="snapshot-1",
            TargetDBClusterSnapshotIdentifier="snapshot-1-copy",
            KmsKeyId=kms_key_id,
        )
    message = f"Specified KMS key [{kms_key_id}] does not exist, is not enabled or you do not have permissions to access it."
    resp = ex.value.response
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert resp["Error"]["Code"] == "KMSKeyNotAccessibleFault"
    assert message in resp["Error"]["Message"]


@mock_aws
def test_copy_db_cluster_snapshot_copy_tags_from_source_snapshot(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap",
        DBClusterIdentifier="cluster-1",
        Tags=test_tags,
    )["DBClusterSnapshot"]
    tag_list = client.list_tags_for_resource(
        ResourceName=snapshot["DBClusterSnapshotArn"]
    )["TagList"]
    assert tag_list == test_tags
    copied_snapshot = client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier="cluster-snap",
        TargetDBClusterSnapshotIdentifier="cluster-snap-copy",
        CopyTags=True,
    )["DBClusterSnapshot"]
    tag_list = client.list_tags_for_resource(
        ResourceName=copied_snapshot["DBClusterSnapshotArn"]
    )["TagList"]
    assert tag_list == test_tags


@mock_aws
def test_copy_db_cluster_snapshot_tags_in_request(client):
    create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
    )
    snapshot = client.create_db_cluster_snapshot(
        DBClusterSnapshotIdentifier="cluster-snap",
        DBClusterIdentifier="cluster-1",
        Tags=test_tags,
    )["DBClusterSnapshot"]
    tag_list = client.list_tags_for_resource(
        ResourceName=snapshot["DBClusterSnapshotArn"]
    )["TagList"]
    assert tag_list == test_tags
    new_snapshot_tags = [
        {
            "Key": "foo",
            "Value": "baz",
        },
    ]
    copied_snapshot = client.copy_db_cluster_snapshot(
        SourceDBClusterSnapshotIdentifier="cluster-snap",
        TargetDBClusterSnapshotIdentifier="cluster-snap-copy",
        Tags=new_snapshot_tags,
        CopyTags=True,
    )["DBClusterSnapshot"]
    tag_list = client.list_tags_for_resource(
        ResourceName=copied_snapshot["DBClusterSnapshotArn"]
    )["TagList"]
    assert tag_list == new_snapshot_tags


@mock_aws
def test_restore_db_cluster_to_point_in_time(client):
    details_source = client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
        Port=1234,
        CopyTagsToSnapshot=True,
    )["DBCluster"]
    details_target = client.restore_db_cluster_to_point_in_time(
        SourceDBClusterIdentifier="cluster-1",
        DBClusterIdentifier="pit-id",
        UseLatestRestorableTime=True,
        # Overrides
        DeletionProtection=True,
        CopyTagsToSnapshot=False,
        Port=4321,
    )["DBCluster"]
    assert details_target["CopyTagsToSnapshot"] != details_source["CopyTagsToSnapshot"]
    assert details_target["DatabaseName"] == details_source["DatabaseName"]
    assert details_target["Port"] != details_source["Port"]
    assert details_target["MasterUsername"] == details_source["MasterUsername"]
    # Overrides
    assert details_target["CopyTagsToSnapshot"] is False
    assert details_target["DeletionProtection"] is True
    assert details_target["Port"] == 4321


@mock_aws
def test_failover_db_cluster(client):
    cluster_identifier = "cluster-1"
    create_db_cluster(
        DBClusterIdentifier=cluster_identifier,
        Engine="aurora-postgresql",
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-primary",
        Engine="aurora-postgresql",
        DBClusterIdentifier=cluster_identifier,
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-replica",
        Engine="aurora-postgresql",
        DBClusterIdentifier=cluster_identifier,
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier=cluster_identifier)[
        "DBClusters"
    ][0]
    cluster_members = cluster["DBClusterMembers"]
    assert len(cluster_members) == 2
    assert cluster_members[0]["DBInstanceIdentifier"] == "test-instance-primary"
    assert cluster_members[0]["IsClusterWriter"] is True
    assert cluster_members[1]["DBInstanceIdentifier"] == "test-instance-replica"
    assert cluster_members[1]["IsClusterWriter"] is False
    cluster_failed_over = client.failover_db_cluster(
        DBClusterIdentifier=cluster_identifier,
        TargetDBInstanceIdentifier="test-instance-replica",
    )["DBCluster"]
    cluster_members = cluster_failed_over["DBClusterMembers"]
    assert len(cluster_members) == 2
    assert cluster_members[0]["DBInstanceIdentifier"] == "test-instance-primary"
    assert cluster_members[0]["IsClusterWriter"] is False
    assert cluster_members[1]["DBInstanceIdentifier"] == "test-instance-replica"
    assert cluster_members[1]["IsClusterWriter"] is True


@mock_aws
def test_failover_db_cluster_without_target_instance_specified(client):
    cluster_identifier = "cluster-1"
    create_db_cluster(
        DBClusterIdentifier=cluster_identifier,
        Engine="aurora-postgresql",
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-primary",
        Engine="aurora-postgresql",
        DBClusterIdentifier=cluster_identifier,
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-replica",
        Engine="aurora-postgresql",
        DBClusterIdentifier=cluster_identifier,
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier=cluster_identifier)[
        "DBClusters"
    ][0]
    cluster_members = cluster["DBClusterMembers"]
    assert len(cluster_members) == 2
    assert cluster_members[0]["DBInstanceIdentifier"] == "test-instance-primary"
    assert cluster_members[0]["IsClusterWriter"] is True
    assert cluster_members[1]["DBInstanceIdentifier"] == "test-instance-replica"
    assert cluster_members[1]["IsClusterWriter"] is False
    cluster_failed_over = client.failover_db_cluster(
        DBClusterIdentifier=cluster_identifier,
    )["DBCluster"]
    cluster_members = cluster_failed_over["DBClusterMembers"]
    assert len(cluster_members) == 2
    assert cluster_members[0]["DBInstanceIdentifier"] == "test-instance-primary"
    assert cluster_members[0]["IsClusterWriter"] is False
    assert cluster_members[1]["DBInstanceIdentifier"] == "test-instance-replica"
    assert cluster_members[1]["IsClusterWriter"] is True


@mock_aws
def test_failover_db_cluster_with_single_instance_cluster(client):
    cluster_identifier = "cluster-1"
    create_db_cluster(
        DBClusterIdentifier=cluster_identifier,
        Engine="aurora-postgresql",
    )
    create_db_instance(
        DBInstanceIdentifier="test-instance-primary",
        Engine="aurora-postgresql",
        DBClusterIdentifier=cluster_identifier,
    )
    cluster = client.describe_db_clusters(DBClusterIdentifier=cluster_identifier)[
        "DBClusters"
    ][0]
    cluster_members = cluster["DBClusterMembers"]
    assert len(cluster_members) == 1
    assert cluster_members[0]["DBInstanceIdentifier"] == "test-instance-primary"
    assert cluster_members[0]["IsClusterWriter"] is True
    with pytest.raises(ClientError) as ex:
        client.failover_db_cluster(
            DBClusterIdentifier=cluster_identifier,
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidDBClusterStateFault"


@mock_aws
def test_failover_db_cluster_exceptions(client):
    with pytest.raises(ClientError) as ex:
        client.failover_db_cluster(
            DBClusterIdentifier="non-existent-cluster",
            TargetDBInstanceIdentifier="non-existent-instance",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    create_db_instance(
        DBInstanceIdentifier="now-existent-instance",
        Engine="postgres",
    )
    with pytest.raises(ClientError) as ex:
        client.failover_db_cluster(
            DBClusterIdentifier="non-existent-cluster",
            TargetDBInstanceIdentifier="now-existent-instance",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "DBClusterNotFoundFault"
    # Real AWS seems to check for the target instance being in a valid state
    # before checking if it is actually part of the cluster, so we can put
    # this non-clustered instance into a stopped state to simulate the error
    # that AWS would return for a target instance in a non-valid state.
    client.stop_db_instance(DBInstanceIdentifier="now-existent-instance")
    with pytest.raises(ClientError) as ex:
        client.failover_db_cluster(
            DBClusterIdentifier="non-existent-cluster",
            TargetDBInstanceIdentifier="now-existent-instance",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidDBInstanceState"


@mock_aws
def test_db_cluster_writer_promotion(client):
    client.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
    )
    for i in range(3):
        client.create_db_instance(
            DBInstanceIdentifier=f"test-instance-{i}",
            DBInstanceClass="db.m1.small",
            Engine="aurora-postgresql",
            DBClusterIdentifier="cluster-1",
            PromotionTier=15 - i,
        )
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1")[
        "DBClusters"
    ][0]
    assert len(cluster["DBClusterMembers"]) == 3
    writer = next(
        i["DBInstanceIdentifier"]
        for i in cluster["DBClusterMembers"]
        if i["IsClusterWriter"]
    )
    assert writer == "test-instance-0"
    client.delete_db_instance(DBInstanceIdentifier="test-instance-0")
    cluster = client.describe_db_clusters(DBClusterIdentifier="cluster-1")[
        "DBClusters"
    ][0]
    assert len(cluster["DBClusterMembers"]) == 2
    writer = next(
        i["DBInstanceIdentifier"]
        for i in cluster["DBClusterMembers"]
        if i["IsClusterWriter"]
    )
    assert writer == "test-instance-2"


@mock_aws
def test_db_cluster_identifier_is_case_insensitive(client):
    cluster = client.create_db_cluster(
        DBClusterIdentifier="FooBar",
        DatabaseName="db_name",
        Engine="aurora-postgresql",
        MasterUsername="root",
        MasterUserPassword="password",
    )["DBCluster"]
    assert cluster["DBClusterIdentifier"] == "foobar"

    for identifier in "foobar", "FOOBAR":
        response = client.describe_db_clusters(DBClusterIdentifier=identifier)
        assert response["DBClusters"][0]["DBClusterIdentifier"] == "foobar"

    response = client.modify_db_cluster(
        DBClusterIdentifier="fOObAR",
        NewDBClusterIdentifier="XxYy",
    )
    assert response["DBCluster"]["DBClusterIdentifier"] == "xxyy"

    instance = create_db_instance(
        DBInstanceIdentifier="clustered-instance",
        DBClusterIdentifier="XxYy",
        Engine="aurora-postgresql",
    )
    assert instance["DBClusterIdentifier"] == "xxyy"
    client.delete_db_instance(DBInstanceIdentifier="clustered-instance")

    response = client.delete_db_cluster(DBClusterIdentifier="xXyY")
    assert response["DBCluster"]["DBClusterIdentifier"] == "xxyy"
