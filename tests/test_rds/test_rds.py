import datetime
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.rds.exceptions import InvalidDBInstanceIdentifier, InvalidDBSnapshotIdentifier
from moto.rds.models import RDSBackend
from tests import aws_verified

DEFAULT_REGION = "us-west-2"


@pytest.fixture(name="client")
@mock_aws
def get_rds_client():
    return boto3.client("rds", region_name=DEFAULT_REGION)


@mock_aws
def test_create_database(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        LicenseModel="license-included",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        VpcSecurityGroupIds=["sg-123456"],
        EnableCloudwatchLogsExports=["audit", "error"],
    )
    db_instance = database["DBInstance"]
    assert db_instance["AllocatedStorage"] == 10
    assert db_instance["DBInstanceClass"] == "db.m1.small"
    assert db_instance["LicenseModel"] == "license-included"
    assert db_instance["MasterUsername"] == "root"
    assert db_instance["DBSecurityGroups"][0]["DBSecurityGroupName"] == "my_sg"
    assert db_instance["DBInstanceArn"] == (
        f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:db:db-master-1"
    )
    assert db_instance["DBInstanceStatus"] == "available"
    assert db_instance["DBName"] == "staging-postgres"
    assert db_instance["DBInstanceIdentifier"] == "db-master-1"
    assert db_instance["IAMDatabaseAuthenticationEnabled"] is False
    assert "db-" in db_instance["DbiResourceId"]
    assert db_instance["CopyTagsToSnapshot"] is False
    assert isinstance(db_instance["InstanceCreateTime"], datetime.datetime)
    assert db_instance["VpcSecurityGroups"][0]["VpcSecurityGroupId"] == "sg-123456"
    assert db_instance["DeletionProtection"] is False
    assert db_instance["EnabledCloudwatchLogsExports"] == ["audit", "error"]
    assert db_instance["Endpoint"]["Port"] == 1234
    assert db_instance["DbInstancePort"] == 1234


@mock_aws
def test_database_with_deletion_protection_cannot_be_deleted(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        DeletionProtection=True,
    )
    db_instance = database["DBInstance"]
    assert db_instance["DBInstanceClass"] == "db.m1.small"
    assert db_instance["DeletionProtection"] is True


@mock_aws
def test_create_database_no_allocated_storage(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
    )
    db_instance = database["DBInstance"]
    assert db_instance["Engine"] == "postgres"
    assert db_instance["StorageType"] == "gp2"
    assert db_instance["AllocatedStorage"] == 20
    assert db_instance["PreferredMaintenanceWindow"] == "wed:06:38-wed:07:08"


@mock_aws
def test_create_database_invalid_preferred_maintenance_window_more_24_hours(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16:00-tue:17:00",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Maintenance window must be less than 24 hours."


@mock_aws
def test_create_database_invalid_preferred_maintenance_window_less_30_mins(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16:00-mon:16:05",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "The maintenance window must be at least 30 minutes."


@mock_aws
def test_create_database_invalid_preferred_maintenance_window_value(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="sim:16:00-mon:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert "Invalid day:hour:minute" in err["Message"]


@mock_aws
def test_create_database_invalid_preferred_maintenance_window_format(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16tue:17:00",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        "Should be specified as a range ddd:hh24:mi-ddd:hh24:mi "
        "(24H Clock UTC). Example: Sun:23:45-Mon:00:15"
    ) in err["Message"]


@mock_aws
def test_create_database_preferred_backup_window_overlap_no_spill(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="wed:18:00-wed:22:00",
            PreferredBackupWindow="20:00-20:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        "The backup window and maintenance window must not overlap." in err["Message"]
    )


@mock_aws
def test_create_database_preferred_backup_window_overlap_maintenance_window_spill(
    client,
):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="wed:18:00-thu:01:00",
            PreferredBackupWindow="00:00-00:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        "The backup window and maintenance window must not overlap." in err["Message"]
    )


@mock_aws
def test_create_database_preferred_backup_window_overlap_backup_window_spill(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="thu:00:00-thu:14:00",
            PreferredBackupWindow="23:50-00:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        "The backup window and maintenance window must not overlap." in err["Message"]
    )


@mock_aws
def test_create_database_preferred_backup_window_overlap_both_spill(client):
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="wed:18:00-thu:01:00",
            PreferredBackupWindow="23:50-00:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        "The backup window and maintenance window must not overlap." in err["Message"]
    )


@mock_aws
def test_create_database_valid_preferred_maintenance_window_format(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        PreferredMaintenanceWindow="sun:16:00-sun:16:30",
    )
    db_instance = database["DBInstance"]
    assert db_instance["DBInstanceClass"] == "db.m1.small"
    assert db_instance["PreferredMaintenanceWindow"] == "sun:16:00-sun:16:30"


@mock_aws
def test_create_database_valid_preferred_maintenance_window_uppercase_format(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        PreferredMaintenanceWindow="MON:16:00-TUE:01:30",
    )
    db_instance = database["DBInstance"]
    assert db_instance["DBInstanceClass"] == "db.m1.small"
    assert db_instance["PreferredMaintenanceWindow"] == "mon:16:00-tue:01:30"


@mock_aws
def test_create_database_non_existing_option_group(client):
    with pytest.raises(ClientError):
        client.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            AllocatedStorage=10,
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            OptionGroupName="non-existing",
        )


@mock_aws
def test_create_database_with_option_group(client):
    client.create_option_group(
        OptionGroupName="my-og",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        OptionGroupName="my-og",
    )
    db_instance = database["DBInstance"]
    assert db_instance["AllocatedStorage"] == 10
    assert db_instance["DBInstanceClass"] == "db.m1.small"
    assert db_instance["DBName"] == "staging-postgres"
    assert db_instance["OptionGroupMemberships"][0]["OptionGroupName"] == "my-og"


@mock_aws
def test_stop_database(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        LicenseModel="license-included",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    mydb = client.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # test stopping database should shutdown
    response = client.stop_db_instance(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"
    # test rdsclient error when trying to stop an already stopped database
    with pytest.raises(ClientError):
        client.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # test stopping a stopped database with snapshot should error and no
    # snapshot should exist for that call
    with pytest.raises(ClientError):
        client.stop_db_instance(
            DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
            DBSnapshotIdentifier="rocky4570-rds-snap",
        )
    response = client.describe_db_snapshots()
    assert response["DBSnapshots"] == []


@mock_aws
def test_start_database(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        LicenseModel="license-included",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    mydb = client.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # test starting an already started database should error
    with pytest.raises(ClientError):
        client.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # stop and test start - should go from stopped to available, create
    # snapshot and check snapshot
    response = client.stop_db_instance(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
        DBSnapshotIdentifier="rocky4570-rds-snap",
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"
    response = client.describe_db_snapshots()
    assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "rocky4570-rds-snap"
    response = client.start_db_instance(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "available"
    # starting database should not remove snapshot
    response = client.describe_db_snapshots()
    assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "rocky4570-rds-snap"
    # test stopping database, create snapshot with existing snapshot already
    # created should throw error
    with pytest.raises(ClientError):
        client.stop_db_instance(
            DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
            DBSnapshotIdentifier="rocky4570-rds-snap",
        )
    # test stopping database not invoking snapshot should succeed.
    response = client.stop_db_instance(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"


@mock_aws
def test_fail_to_stop_multi_az_and_sqlserver(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="sqlserver-ee",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        LicenseModel="license-included",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        MultiAZ=True,
    )

    mydb = client.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # multi-az databases arent allowed to be shutdown at this time.
    with pytest.raises(ClientError):
        client.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # multi-az databases arent allowed to be started up at this time.
    with pytest.raises(ClientError):
        client.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])


@mock_aws
def test_stop_multi_az_postgres(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        LicenseModel="license-included",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        MultiAZ=True,
    )

    mydb = client.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"

    response = client.stop_db_instance(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"


@mock_aws
def test_fail_to_stop_readreplica(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        LicenseModel="license-included",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    replica = client.create_db_instance_read_replica(
        DBInstanceIdentifier="db-replica-1",
        SourceDBInstanceIdentifier="db-master-1",
        DBInstanceClass="db.m1.small",
    )

    mydb = client.describe_db_instances(
        DBInstanceIdentifier=replica["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # read-replicas are not allowed to be stopped at this time.
    with pytest.raises(ClientError):
        client.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # read-replicas are not allowed to be started at this time.
    with pytest.raises(ClientError):
        client.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])


@mock_aws
def test_get_databases(client):
    instances = client.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 0

    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    client.create_db_instance(
        DBInstanceIdentifier="db-master-2",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        DeletionProtection=True,
    )
    instances = client.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 2

    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert len(list(instances["DBInstances"])) == 1
    assert instances["DBInstances"][0]["DBInstanceIdentifier"] == "db-master-1"
    assert instances["DBInstances"][0]["DeletionProtection"] is False
    assert instances["DBInstances"][0]["DBInstanceArn"] == (
        f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:db:db-master-1"
    )

    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-2")
    assert instances["DBInstances"][0]["DeletionProtection"] is True
    assert instances["DBInstances"][0]["Endpoint"]["Port"] == 1234
    assert instances["DBInstances"][0]["DbInstancePort"] == 1234


@mock_aws
def test_get_databases_paginated(client):
    for i in range(51):
        client.create_db_instance(
            AllocatedStorage=5,
            Port=5432,
            DBInstanceIdentifier=f"rds{i}",
            DBInstanceClass="db.t1.micro",
            Engine="postgres",
        )

    resp = client.describe_db_instances()
    assert len(resp["DBInstances"]) == 50
    assert resp["Marker"] == resp["DBInstances"][-1]["DBInstanceIdentifier"]

    resp2 = client.describe_db_instances(Marker=resp["Marker"])
    assert len(resp2["DBInstances"]) == 1

    resp3 = client.describe_db_instances(MaxRecords=100)
    assert len(resp3["DBInstances"]) == 51


@mock_aws
def test_describe_non_existent_database(client):
    with pytest.raises(ClientError):
        client.describe_db_instances(DBInstanceIdentifier="not-a-db")


@pytest.mark.parametrize(
    "custom_db_subnet_group", [True, False], ids=("custom_subnet", "default_subnet")
)
@mock_aws
def test_modify_db_instance(custom_db_subnet_group: bool, client):
    if custom_db_subnet_group:
        extra_kwargs = {"DBSubnetGroupName": create_db_subnet_group()}
    else:
        extra_kwargs = {}

    client.create_db_instance(
        DBInstanceIdentifier="db-id",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        **extra_kwargs,
    )
    inst = client.describe_db_instances(DBInstanceIdentifier="db-id")["DBInstances"][0]
    assert inst["AllocatedStorage"] == 10
    assert inst["EnabledCloudwatchLogsExports"] == []

    client.modify_db_instance(
        DBInstanceIdentifier="db-id",
        AllocatedStorage=20,
        ApplyImmediately=True,
        VpcSecurityGroupIds=["sg-123456"],
        CloudwatchLogsExportConfiguration={"EnableLogTypes": ["error"]},
    )
    inst = client.describe_db_instances(DBInstanceIdentifier="db-id")["DBInstances"][0]
    assert inst["AllocatedStorage"] == 20
    assert inst["PreferredMaintenanceWindow"] == "wed:06:38-wed:07:08"
    assert inst["VpcSecurityGroups"][0]["VpcSecurityGroupId"] == "sg-123456"
    assert inst["EnabledCloudwatchLogsExports"] == ["error"]


@pytest.mark.parametrize("with_custom_kms_key", [True, False])
@mock_aws
def test_modify_db_instance_manage_master_user_password(
    with_custom_kms_key: bool, client
):
    db_id = "db-id"

    custom_kms_key = f"arn:aws:kms:{DEFAULT_REGION}:123456789012:key/abcd1234-56ef-78gh-90ij-klmnopqrstuv"
    custom_kms_key_args = (
        {"MasterUserSecretKmsKeyId": custom_kms_key} if with_custom_kms_key else {}
    )

    create_response = client.create_db_instance(
        DBInstanceIdentifier=db_id,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter21",
        ManageMasterUserPassword=False,
    )

    modify_response = client.modify_db_instance(
        DBInstanceIdentifier=db_id, ManageMasterUserPassword=True, **custom_kms_key_args
    )

    describe_response = client.describe_db_instances(DBInstanceIdentifier=db_id)

    revert_modification_response = client.modify_db_instance(
        DBInstanceIdentifier=db_id, ManageMasterUserPassword=False
    )

    assert create_response["DBInstance"].get("MasterUserSecret") is None
    master_user_secret = modify_response["DBInstance"]["MasterUserSecret"]
    assert len(master_user_secret.keys()) == 3
    assert (
        master_user_secret["SecretArn"]
        == "arn:aws:secretsmanager:us-west-2:123456789012:secret:rds!db-id"
    )
    assert master_user_secret["SecretStatus"] == "active"
    if with_custom_kms_key:
        assert master_user_secret["KmsKeyId"] == custom_kms_key
    else:
        assert (
            master_user_secret["KmsKeyId"]
            == "arn:aws:kms:us-west-2:123456789012:key/db-id"
        )
    assert len(describe_response["DBInstances"][0]["MasterUserSecret"].keys()) == 3
    assert (
        modify_response["DBInstance"]["MasterUserSecret"]
        == describe_response["DBInstances"][0]["MasterUserSecret"]
    )
    assert revert_modification_response["DBInstance"].get("MasterUserSecret") is None


@pytest.mark.parametrize("with_apply_immediately", [True, False])
@mock_aws
def test_modify_db_instance_rotate_master_user_password(with_apply_immediately, client):
    db_id = "db-id"

    client.create_db_instance(
        DBInstanceIdentifier=db_id,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter21",
        ManageMasterUserPassword=True,
    )

    if with_apply_immediately:
        modify_response = client.modify_db_instance(
            DBInstanceIdentifier=db_id,
            RotateMasterUserPassword=True,
            ApplyImmediately=True,
        )

        describe_response = client.describe_db_instances(
            DBInstanceIdentifier=db_id,
        )

        assert (
            modify_response["DBInstance"]["MasterUserSecret"]["SecretStatus"]
            == "rotating"
        )
        assert (
            describe_response["DBInstances"][0]["MasterUserSecret"]["SecretStatus"]
            == "active"
        )

    else:
        with pytest.raises(ClientError):
            client.modify_db_instance(
                DBInstanceIdentifier=db_id,
                RotateMasterUserPassword=True,
            )


@mock_aws
def test_modify_db_instance_not_existent_db_parameter_group_name(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["AllocatedStorage"] == 10
    with pytest.raises(ClientError):
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            DBParameterGroupName="test-sqlserver-se-2017",
        )


@mock_aws
def test_modify_db_instance_valid_preferred_maintenance_window(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    client.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        PreferredMaintenanceWindow="sun:16:00-sun:16:30",
    )
    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["PreferredMaintenanceWindow"] == (
        "sun:16:00-sun:16:30"
    )


@mock_aws
def test_modify_db_instance_valid_preferred_maintenance_window_uppercase(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    client.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        PreferredMaintenanceWindow="SUN:16:00-SUN:16:30",
    )
    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["PreferredMaintenanceWindow"] == (
        "sun:16:00-sun:16:30"
    )


@mock_aws
def test_modify_db_instance_invalid_preferred_maintenance_window_more_than_24_hours(
    client,
):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-sat:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Maintenance window must be less than 24 hours."


@mock_aws
def test_modify_db_instance_invalid_preferred_maintenance_window_less_than_30_mins(
    client,
):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-sun:16:10",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "The maintenance window must be at least 30 minutes."


@mock_aws
def test_modify_db_instance_invalid_preferred_maintenance_window_value(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sin:16:00-sun:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert "Invalid day:hour:minute value" in err["Message"]


@mock_aws
def test_modify_db_instance_invalid_preferred_maintenance_window_format(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00sun:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        "Should be specified as a range ddd:hh24:mi-ddd:hh24:mi "
        "(24H Clock UTC). Example: Sun:23:45-Mon:00:15"
    ) in err["Message"]


@mock_aws
def test_modify_db_instance_maintenance_backup_window_no_spill(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-sun:16:30",
            PreferredBackupWindow="15:50-16:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"] == "The backup window and maintenance window must not overlap."
    )


@mock_aws
def test_modify_db_instance_maintenance_backup_window_maintenance_spill(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-mon:15:00",
            PreferredBackupWindow="00:00-00:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The backup window and maintenance window must not overlap."
    )


@mock_aws
def test_modify_db_instance_maintenance_backup_window_backup_spill(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="mon:00:00-mon:15:00",
            PreferredBackupWindow="23:50-00:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The backup window and maintenance window must not overlap."
    )


@mock_aws
def test_modify_db_instance_maintenance_backup_window_both_spill(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        client.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-mon:15:00",
            PreferredBackupWindow="23:20-00:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The backup window and maintenance window must not overlap."
    )


@mock_aws
def test_rename_db_instance(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert len(list(instances["DBInstances"])) == 1
    with pytest.raises(ClientError):
        client.describe_db_instances(DBInstanceIdentifier="db-master-2")
    client.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        NewDBInstanceIdentifier="db-master-2",
        ApplyImmediately=True,
    )
    with pytest.raises(ClientError):
        client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    instances = client.describe_db_instances(DBInstanceIdentifier="db-master-2")
    assert len(list(instances["DBInstances"])) == 1


@mock_aws
def test_modify_non_existent_database(client):
    with pytest.raises(ClientError):
        client.modify_db_instance(
            DBInstanceIdentifier="not-a-db", AllocatedStorage=20, ApplyImmediately=True
        )


@mock_aws
def test_reboot_db_instance(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    database = client.reboot_db_instance(DBInstanceIdentifier="db-master-1")
    assert database["DBInstance"]["DBInstanceIdentifier"] == "db-master-1"


@mock_aws
def test_reboot_non_existent_database(client):
    with pytest.raises(ClientError):
        client.reboot_db_instance(DBInstanceIdentifier="not-a-db")


@mock_aws
def test_delete_database(client):
    instances = client.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 0
    client.create_db_instance(
        DBInstanceIdentifier="db-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = client.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 1

    client.delete_db_instance(
        DBInstanceIdentifier="db-1",
        FinalDBSnapshotIdentifier="primary-1-snapshot",
    )

    instances = client.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 0

    # Saved the snapshot
    snapshot = client.describe_db_snapshots(DBInstanceIdentifier="db-1")["DBSnapshots"][
        0
    ]
    assert snapshot["Engine"] == "postgres"
    assert snapshot["SnapshotType"] == "automated"


@mock_aws
def test_create_db_snapshots(client):
    with pytest.raises(ClientError):
        client.create_db_snapshot(
            DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
        )

    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    snapshot = client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="g-1"
    ).get("DBSnapshot")

    assert snapshot.get("Engine") == "postgres"
    assert snapshot.get("DBInstanceIdentifier") == "db-primary-1"
    assert snapshot.get("DBSnapshotIdentifier") == "g-1"
    result = client.list_tags_for_resource(ResourceName=snapshot["DBSnapshotArn"])
    assert result["TagList"] == []


@mock_aws
def test_create_db_snapshots_copy_tags(client):
    with pytest.raises(ClientError):
        client.create_db_snapshot(
            DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
        )

    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        CopyTagsToSnapshot=True,
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )

    snapshot = client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="g-1"
    ).get("DBSnapshot")

    assert snapshot.get("Engine") == "postgres"
    assert snapshot.get("DBInstanceIdentifier") == "db-primary-1"
    assert snapshot.get("DBSnapshotIdentifier") == "g-1"
    result = client.list_tags_for_resource(ResourceName=snapshot["DBSnapshotArn"])
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_create_db_snapshots_with_tags(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="g-1",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )

    snapshots = client.describe_db_snapshots(DBInstanceIdentifier="db-primary-1").get(
        "DBSnapshots"
    )
    assert snapshots[0].get("DBSnapshotIdentifier") == "g-1"
    assert snapshots[0].get("TagList") == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@pytest.mark.parametrize("delete_db_instance", [True, False])
@pytest.mark.parametrize(
    "db_snapshot_identifier",
    ("snapshot-1", f"arn:aws:rds:{DEFAULT_REGION}:123456789012:snapshot:snapshot-1"),
    ids=("by_name", "by_arn"),
)
@mock_aws
def test_copy_db_snapshots(
    delete_db_instance: bool, db_snapshot_identifier: str, client
):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshot")

    if delete_db_instance:
        # Delete the original instance, but the copy snapshot operation should still succeed.
        client.delete_db_instance(DBInstanceIdentifier="db-primary-1")

    target_snapshot = client.copy_db_snapshot(
        SourceDBSnapshotIdentifier=db_snapshot_identifier,
        TargetDBSnapshotIdentifier="snapshot-2",
    ).get("DBSnapshot")

    assert target_snapshot.get("Engine") == "postgres"
    assert target_snapshot.get("DBInstanceIdentifier") == "db-primary-1"
    assert target_snapshot.get("DBSnapshotIdentifier") == "snapshot-2"
    result = client.list_tags_for_resource(
        ResourceName=target_snapshot["DBSnapshotArn"]
    )
    assert result["TagList"] == []


@mock_aws
def test_copy_db_snapshot_invalid_arns(client):
    invalid_arn = (
        f"arn:aws:rds:{DEFAULT_REGION}:123456789012:this-is-not-a-snapshot:snapshot-1"
    )
    with pytest.raises(ClientError) as ex:
        client.copy_db_snapshot(
            SourceDBSnapshotIdentifier=invalid_arn,
            TargetDBSnapshotIdentifier="snapshot-2",
        )
    assert "is not a valid identifier" in ex.value.response["Error"]["Message"]


original_snapshot_tags = [{"Key": "original", "Value": "snapshot tags"}]
new_snapshot_tags = [{"Key": "new", "Value": "tag"}]


@pytest.mark.parametrize(
    "kwargs,expected_tags",
    [
        # No Tags parameter, CopyTags defaults to False -> no tags
        ({}, []),
        # No Tags parameter, CopyTags set to True -> use tags of original snapshot
        ({"CopyTags": True}, original_snapshot_tags),
        # When "Tags" are given, they become the only tags of the snapshot.
        ({"Tags": new_snapshot_tags}, new_snapshot_tags),
        # When "Tags" are given, they become the only tags of the snapshot. Even if CopyTags is True!
        ({"Tags": new_snapshot_tags, "CopyTags": True}, new_snapshot_tags),
        # When "Tags" are given but empty, CopyTags=True takes effect again!
        ({"Tags": [], "CopyTags": True}, original_snapshot_tags),
    ],
    ids=(
        "no_parameters",
        "copytags_true",
        "only_tags",
        "copytags_true_and_tags",
        "copytags_true_and_empty_tags",
    ),
)
@mock_aws
def test_copy_db_snapshots_copytags_and_tags(kwargs, expected_tags, client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        Engine="postgres",
        DBInstanceClass="db.m1.small",
    )
    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="snapshot",
        Tags=original_snapshot_tags,
    )

    target_snapshot = client.copy_db_snapshot(
        SourceDBSnapshotIdentifier="snapshot",
        TargetDBSnapshotIdentifier="snapshot-copy",
        **kwargs,
    ).get("DBSnapshot")
    result = client.list_tags_for_resource(
        ResourceName=target_snapshot["DBSnapshotArn"]
    )
    assert result["TagList"] == expected_tags


@mock_aws
def test_describe_db_snapshots(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    created = client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshot")

    assert created["Engine"] == "postgres"
    assert created["SnapshotType"] == "manual"

    by_database_id = client.describe_db_snapshots(
        DBInstanceIdentifier="db-primary-1"
    ).get("DBSnapshots")
    by_snapshot_id = client.describe_db_snapshots(
        DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshots")
    assert by_snapshot_id == by_database_id

    snapshot = by_snapshot_id[0]
    assert snapshot == created

    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-2"
    )
    snapshots = client.describe_db_snapshots(DBInstanceIdentifier="db-primary-1").get(
        "DBSnapshots"
    )
    assert len(snapshots) == 2


@mock_aws
def test_promote_read_replica(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    client.create_db_instance_read_replica(
        DBInstanceIdentifier="db-replica-1",
        SourceDBInstanceIdentifier="db-primary-1",
        DBInstanceClass="db.m1.small",
    )
    client.promote_read_replica(DBInstanceIdentifier="db-replica-1")

    replicas = client.describe_db_instances(DBInstanceIdentifier="db-primary-1").get(
        "ReadReplicaDBInstanceIdentifiers"
    )
    assert replicas is None


@mock_aws
def test_delete_db_snapshot(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    )

    _ = client.describe_db_snapshots(DBSnapshotIdentifier="snapshot-1").get(
        "DBSnapshots"
    )[0]
    client.delete_db_snapshot(DBSnapshotIdentifier="snapshot-1")
    with pytest.raises(ClientError):
        client.describe_db_snapshots(DBSnapshotIdentifier="snapshot-1")


@pytest.mark.parametrize(
    "db_snapshot_identifier",
    ("snapshot-1", f"arn:aws:rds:{DEFAULT_REGION}:123456789012:snapshot:snapshot-1"),
    ids=("by_name", "by_arn"),
)
@pytest.mark.parametrize(
    "custom_db_subnet_group", [True, False], ids=("custom_subnet", "default_subnet")
)
@mock_aws
def test_restore_db_instance_from_db_snapshot(
    db_snapshot_identifier: str, custom_db_subnet_group: bool, client
):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        DBSecurityGroups=["my_sg"],
    )
    assert len(client.describe_db_instances()["DBInstances"]) == 1

    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    )

    if custom_db_subnet_group:
        db_subnet_group_name = create_db_subnet_group()

    # restore
    new_instance = client.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier="db-restore-1", DBSnapshotIdentifier=db_snapshot_identifier
    )["DBInstance"]
    kwargs = {
        "DBInstanceIdentifier": "db-restore-1",
        "DBSnapshotIdentifier": db_snapshot_identifier,
    }
    if custom_db_subnet_group:
        kwargs["DBSubnetGroupName"] = db_subnet_group_name
    new_instance = client.restore_db_instance_from_db_snapshot(**kwargs)["DBInstance"]
    if custom_db_subnet_group:
        assert (
            new_instance["DBSubnetGroup"]["DBSubnetGroupName"] == db_subnet_group_name
        )
    assert new_instance["DBInstanceIdentifier"] == "db-restore-1"
    assert new_instance["DBInstanceClass"] == "db.m1.small"
    assert new_instance["StorageType"] == "gp2"
    assert new_instance["Engine"] == "postgres"
    assert new_instance["DBName"] == "staging-postgres"
    assert new_instance["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "default.postgres9.3"
    )
    assert new_instance["DBSecurityGroups"] == [
        {"DBSecurityGroupName": "my_sg", "Status": "active"}
    ]
    assert new_instance["Endpoint"]["Port"] == 5432

    # Verify it exists
    assert len(client.describe_db_instances()["DBInstances"]) == 2
    assert (
        len(
            client.describe_db_instances(DBInstanceIdentifier="db-restore-1")[
                "DBInstances"
            ]
        )
        == 1
    )


@pytest.mark.parametrize(
    "custom_db_subnet_group", [True, False], ids=("custom_subnet", "default_subnet")
)
@mock_aws
def test_restore_db_instance_to_point_in_time(custom_db_subnet_group: bool, client):
    if custom_db_subnet_group:
        extra_kwargs = {"DBSubnetGroupName": create_db_subnet_group()}
    else:
        extra_kwargs = {}

    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        DBSecurityGroups=["my_sg"],
        **extra_kwargs,
    )
    assert len(client.describe_db_instances()["DBInstances"]) == 1

    # restore
    new_instance = client.restore_db_instance_to_point_in_time(
        SourceDBInstanceIdentifier="db-primary-1",
        TargetDBInstanceIdentifier="db-restore-1",
    )["DBInstance"]
    assert new_instance["DBInstanceIdentifier"] == "db-restore-1"
    assert new_instance["DBInstanceClass"] == "db.m1.small"
    assert new_instance["StorageType"] == "gp2"
    assert new_instance["Engine"] == "postgres"
    assert new_instance["DBName"] == "staging-postgres"
    assert new_instance["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "default.postgres9.3"
    )
    assert new_instance["DBSecurityGroups"] == [
        {"DBSecurityGroupName": "my_sg", "Status": "active"}
    ]
    assert new_instance["Endpoint"]["Port"] == 5432

    # Verify it exists
    assert len(client.describe_db_instances()["DBInstances"]) == 2
    assert (
        len(
            client.describe_db_instances(DBInstanceIdentifier="db-restore-1")[
                "DBInstances"
            ]
        )
        == 1
    )
    # ensure another pit restore can be made
    new_instance = client.restore_db_instance_to_point_in_time(
        SourceDBInstanceIdentifier="db-primary-1",
        TargetDBInstanceIdentifier="db-restore-2",
    )["DBInstance"]
    assert new_instance["DBInstanceIdentifier"] == "db-restore-2"
    assert new_instance["DBInstanceClass"] == "db.m1.small"
    assert new_instance["StorageType"] == "gp2"
    assert new_instance["Engine"] == "postgres"
    assert new_instance["DBName"] == "staging-postgres"
    assert new_instance["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "default.postgres9.3"
    )
    assert new_instance["DBSecurityGroups"] == [
        {"DBSecurityGroupName": "my_sg", "Status": "active"}
    ]
    assert new_instance["Endpoint"]["Port"] == 5432

    # Verify it exists
    assert len(client.describe_db_instances()["DBInstances"]) == 3
    assert (
        len(
            client.describe_db_instances(DBInstanceIdentifier="db-restore-2")[
                "DBInstances"
            ]
        )
        == 1
    )


@mock_aws
def test_restore_db_instance_from_db_snapshot_and_override_params(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    assert len(client.describe_db_instances()["DBInstances"]) == 1
    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    )

    # restore with some updated attributes
    new_instance = client.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier="db-restore-1",
        DBSnapshotIdentifier="snapshot-1",
        Port=10000,
        VpcSecurityGroupIds=["new_vpc"],
    )["DBInstance"]
    assert new_instance["DBInstanceIdentifier"] == "db-restore-1"
    assert new_instance["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "default.postgres9.3"
    )
    assert new_instance["DBSecurityGroups"] == [
        {"DBSecurityGroupName": "my_sg", "Status": "active"}
    ]
    assert new_instance["VpcSecurityGroups"] == [
        {"VpcSecurityGroupId": "new_vpc", "Status": "active"}
    ]
    assert new_instance["Endpoint"]["Port"] == 10000


@mock_aws
def test_create_option_group(client):
    option_group = client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    assert option_group["OptionGroup"]["OptionGroupName"] == "test"
    assert option_group["OptionGroup"]["EngineName"] == "mysql"
    assert option_group["OptionGroup"]["OptionGroupDescription"] == (
        "test option group"
    )
    assert option_group["OptionGroup"]["MajorEngineVersion"] == "5.6"
    assert option_group["OptionGroup"]["OptionGroupArn"] == (
        f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:og:test"
    )


@mock_aws
def test_create_option_group_bad_engine_name(client):
    with pytest.raises(ClientError):
        client.create_option_group(
            OptionGroupName="test",
            EngineName="invalid_engine",
            MajorEngineVersion="5.6",
            OptionGroupDescription="test invalid engine",
        )


@mock_aws
def test_create_option_group_bad_engine_major_version(client):
    with pytest.raises(ClientError):
        client.create_option_group(
            OptionGroupName="test",
            EngineName="mysql",
            MajorEngineVersion="6.6.6",
            OptionGroupDescription="test invalid engine version",
        )


@mock_aws
def test_create_option_group_empty_description(client):
    with pytest.raises(ClientError):
        client.create_option_group(
            OptionGroupName="test",
            EngineName="mysql",
            MajorEngineVersion="5.6",
            OptionGroupDescription="",
        )


@mock_aws
def test_create_option_group_duplicate(client):
    client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    with pytest.raises(ClientError):
        client.create_option_group(
            OptionGroupName="test",
            EngineName="mysql",
            MajorEngineVersion="5.6",
            OptionGroupDescription="test option group",
        )


@mock_aws
def test_describe_option_group(client):
    client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = client.describe_option_groups(OptionGroupName="test")
    assert option_groups["OptionGroupsList"][0]["OptionGroupName"] == "test"


@mock_aws
def test_describe_non_existent_option_group(client):
    with pytest.raises(ClientError):
        client.describe_option_groups(OptionGroupName="not-a-option-group")


@mock_aws
def test_delete_option_group(client):
    client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = client.describe_option_groups(OptionGroupName="test")
    assert option_groups["OptionGroupsList"][0]["OptionGroupName"] == "test"
    client.delete_option_group(OptionGroupName="test")
    with pytest.raises(ClientError):
        client.describe_option_groups(OptionGroupName="test")


@mock_aws
def test_delete_non_existent_option_group(client):
    with pytest.raises(ClientError):
        client.delete_option_group(OptionGroupName="non-existent")


@mock_aws
def test_describe_option_group_options(client):
    option_group_options = client.describe_option_group_options(
        EngineName="sqlserver-ee"
    )
    assert len(option_group_options["OptionGroupOptions"]) == 4
    option_group_options = client.describe_option_group_options(
        EngineName="sqlserver-ee", MajorEngineVersion="11.00"
    )
    assert len(option_group_options["OptionGroupOptions"]) == 2
    option_group_options = client.describe_option_group_options(
        EngineName="mysql", MajorEngineVersion="5.6"
    )
    assert len(option_group_options["OptionGroupOptions"]) == 1
    with pytest.raises(ClientError):
        client.describe_option_group_options(EngineName="non-existent")
    with pytest.raises(ClientError):
        client.describe_option_group_options(
            EngineName="mysql", MajorEngineVersion="non-existent"
        )


@pytest.mark.aws_verified
@aws_verified
def test_modify_option_group(client):
    option_group_name = f"og-{str(uuid4())[0:6]}"
    client.create_option_group(
        OptionGroupName=option_group_name,
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )

    try:
        # Verify OptionsToRemove do not have to exist
        option_group = client.modify_option_group(
            OptionGroupName=option_group_name,
            OptionsToInclude=[],
            OptionsToRemove=["MEMCACHED"],
            ApplyImmediately=True,
        )["OptionGroup"]
        assert option_group["EngineName"] == "mysql"
        assert option_group["Options"] == []
        assert option_group["OptionGroupName"] == option_group_name

        option_groups = client.describe_option_groups(
            OptionGroupName=option_group_name
        )["OptionGroupsList"]
        assert option_groups[0]["Options"] == []

        # Include option
        # https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Appendix.MySQL.Options.AuditPlugin.html
        client.modify_option_group(
            OptionGroupName=option_group_name,
            OptionsToInclude=[{"OptionName": "MARIADB_AUDIT_PLUGIN"}],
            OptionsToRemove=[],
            ApplyImmediately=True,
        )["OptionGroup"]

        # Verify it was added successfully
        option_groups = client.describe_option_groups(
            OptionGroupName=option_group_name
        )["OptionGroupsList"]

        options = option_groups[0]["Options"]
        assert len(options) == 1
        assert options[0]["OptionName"] == "MARIADB_AUDIT_PLUGIN"
        # AWS automatically adds a description + default option settings, but Moto does not support that yet

        # Change setting for an existing option
        client.modify_option_group(
            OptionGroupName=option_group_name,
            OptionsToInclude=[
                {
                    "OptionName": "MARIADB_AUDIT_PLUGIN",
                    "OptionSettings": [
                        {"Name": "SERVER_AUDIT_FILE_ROTATE_SIZE", "Value": "1000"},
                    ],
                }
            ],
            ApplyImmediately=True,
        )["OptionGroup"]

        # Verify it was added successfully
        option_groups = client.describe_option_groups(
            OptionGroupName=option_group_name
        )["OptionGroupsList"]

        options = option_groups[0]["Options"]
        assert len(options) == 1
        assert options[0]["OptionName"] == "MARIADB_AUDIT_PLUGIN"

        option_settings = options[0]["OptionSettings"]
        audit_plugin = [
            o for o in option_settings if o["Name"] == "SERVER_AUDIT_FILE_ROTATE_SIZE"
        ][0]
        audit_plugin["Name"] == "SERVER_AUDIT_FILE_ROTATE_SIZE"
        audit_plugin["Value"] == "1000"

        # Verify option can be deleted
        client.modify_option_group(
            OptionGroupName=option_group_name,
            OptionsToRemove=["MARIADB_AUDIT_PLUGIN"],
            ApplyImmediately=True,
        )
        option_groups = client.describe_option_groups(
            OptionGroupName=option_group_name
        )["OptionGroupsList"]
        assert option_groups[0]["Options"] == []
    finally:
        client.delete_option_group(OptionGroupName=option_group_name)


@mock_aws
def test_modify_option_group_no_options(client):
    client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    with pytest.raises(ClientError):
        client.modify_option_group(OptionGroupName="test")


@mock_aws
def test_modify_non_existent_option_group(client):
    with pytest.raises(ClientError) as client_err:
        client.modify_option_group(
            OptionGroupName="non-existent",
            OptionsToInclude=[{"OptionName": "test-option"}],
        )
    assert client_err.value.response["Error"]["Message"] == (
        "Specified OptionGroupName: non-existent not found."
    )


@mock_aws
def test_delete_database_with_protection(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        DeletionProtection=True,
    )

    with pytest.raises(ClientError) as exc:
        client.delete_db_instance(DBInstanceIdentifier="db-primary-1")
    err = exc.value.response["Error"]
    assert err["Message"] == "Can't delete Instance with protection enabled"


@mock_aws
def test_delete_non_existent_database(client):
    with pytest.raises(ClientError) as ex:
        client.delete_db_instance(DBInstanceIdentifier="non-existent")
    assert ex.value.response["Error"]["Code"] == "DBInstanceNotFound"
    assert ex.value.response["Error"]["Message"] == "DBInstance non-existent not found."


@mock_aws
def test_list_tags_invalid_arn(client):
    with pytest.raises(ClientError):
        client.list_tags_for_resource(ResourceName="arn:aws:rds:bad-arn")


@mock_aws
def test_list_tags_db(client):
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:foo"
    )
    assert result["TagList"] == []
    test_instance = client.create_db_instance(
        DBInstanceIdentifier="db-with-tags",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = client.list_tags_for_resource(
        ResourceName=test_instance["DBInstance"]["DBInstanceArn"]
    )
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_add_tags_db(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-without-tags",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags"
    )
    assert len(list(result["TagList"])) == 2
    client.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags"
    )
    assert len(list(result["TagList"])) == 3


@mock_aws
def test_remove_tags_db(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-with-tags",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags"
    )
    assert len(list(result["TagList"])) == 2
    client.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags", TagKeys=["foo"]
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags"
    )
    assert len(result["TagList"]) == 1


@mock_aws
def test_list_tags_snapshot(client):
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:foo"
    )
    assert result["TagList"] == []
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    snapshot = client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="snapshot-with-tags",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = client.list_tags_for_resource(
        ResourceName=snapshot["DBSnapshot"]["DBSnapshotArn"]
    )
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_add_tags_snapshot(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="snapshot-without-tags",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags"
    )
    assert len(list(result["TagList"])) == 2
    client.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags"
    )
    assert len(list(result["TagList"])) == 3


@mock_aws
def test_remove_tags_snapshot(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="snapshot-with-tags",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags"
    )
    assert len(list(result["TagList"])) == 2
    client.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags",
        TagKeys=["foo"],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags"
    )
    assert len(result["TagList"]) == 1


@mock_aws
def test_add_tags_option_group(client):
    client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 0
    client.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 2


@mock_aws
def test_remove_tags_option_group(client):
    client.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    client.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 2
    client.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test", TagKeys=["foo"]
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 1


@mock_aws
def test_create_database_security_group(client):
    result = client.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    assert result["DBSecurityGroup"]["DBSecurityGroupName"] == "db_sg"
    assert (
        result["DBSecurityGroup"]["DBSecurityGroupDescription"] == "DB Security Group"
    )
    assert result["DBSecurityGroup"]["IPRanges"] == []


@mock_aws
def test_get_security_groups(client):
    result = client.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 0

    client.create_db_security_group(
        DBSecurityGroupName="db_sg1", DBSecurityGroupDescription="DB Security Group"
    )
    client.create_db_security_group(
        DBSecurityGroupName="db_sg2", DBSecurityGroupDescription="DB Security Group"
    )

    result = client.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 2

    result = client.describe_db_security_groups(DBSecurityGroupName="db_sg1")
    assert len(result["DBSecurityGroups"]) == 1
    assert result["DBSecurityGroups"][0]["DBSecurityGroupName"] == "db_sg1"


@mock_aws
def test_get_non_existent_security_group(client):
    with pytest.raises(ClientError):
        client.describe_db_security_groups(DBSecurityGroupName="not-a-sg")


@mock_aws
def test_delete_database_security_group(client):
    client.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )

    result = client.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 1

    client.delete_db_security_group(DBSecurityGroupName="db_sg")
    result = client.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 0


@mock_aws
def test_delete_non_existent_security_group(client):
    with pytest.raises(ClientError):
        client.delete_db_security_group(DBSecurityGroupName="not-a-db")


@mock_aws
def test_security_group_authorize(client):
    security_group = client.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    assert security_group["DBSecurityGroup"]["IPRanges"] == []

    client.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.45/32"
    )

    result = client.describe_db_security_groups(DBSecurityGroupName="db_sg")
    assert len(result["DBSecurityGroups"][0]["IPRanges"]) == 1
    assert result["DBSecurityGroups"][0]["IPRanges"] == [
        {"Status": "authorized", "CIDRIP": "10.3.2.45/32"}
    ]

    client.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.46/32"
    )
    result = client.describe_db_security_groups(DBSecurityGroupName="db_sg")
    assert len(result["DBSecurityGroups"][0]["IPRanges"]) == 2
    assert result["DBSecurityGroups"][0]["IPRanges"] == [
        {"Status": "authorized", "CIDRIP": "10.3.2.45/32"},
        {"Status": "authorized", "CIDRIP": "10.3.2.46/32"},
    ]


@mock_aws
def test_add_security_group_to_database(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="postgres",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    result = client.describe_db_instances()
    assert result["DBInstances"][0]["DBSecurityGroups"] == []
    client.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    client.modify_db_instance(
        DBInstanceIdentifier="db-master-1", DBSecurityGroups=["db_sg"]
    )
    result = client.describe_db_instances()
    assert (
        result["DBInstances"][0]["DBSecurityGroups"][0]["DBSecurityGroupName"]
        == "db_sg"
    )


@mock_aws
def test_list_tags_security_group(client):
    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    security_group = client.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSecurityGroup"]["DBSecurityGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_add_tags_security_group(client):
    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    security_group = client.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    client.add_tags_to_resource(
        ResourceName=resource,
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )

    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_remove_tags_security_group(client):
    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    security_group = client.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    client.remove_tags_from_resource(ResourceName=resource, TagKeys=["foo"])

    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [{"Value": "bar1", "Key": "foo1"}]


@mock_aws
def test_create_database_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]
    subnet2 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.2.0/24")[
        "Subnet"
    ]

    subnet_ids = [subnet1["SubnetId"], subnet2["SubnetId"]]
    result = client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=subnet_ids,
    )
    assert result["DBSubnetGroup"]["DBSubnetGroupName"] == "db_subnet"
    assert result["DBSubnetGroup"]["DBSubnetGroupDescription"] == "my db subnet"
    subnets = result["DBSubnetGroup"]["Subnets"]
    subnet_group_ids = [subnets[0]["SubnetIdentifier"], subnets[1]["SubnetIdentifier"]]
    assert list(subnet_group_ids) == subnet_ids


@mock_aws
def test_modify_database_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]
    subnet2 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.2.0/24")[
        "Subnet"
    ]

    client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet1["SubnetId"]],
    )

    client.modify_db_subnet_group(
        DBSubnetGroupName="db_subnet",
        DBSubnetGroupDescription="my updated desc",
        SubnetIds=[subnet1["SubnetId"], subnet2["SubnetId"]],
    )

    _ = client.describe_db_subnet_groups()["DBSubnetGroups"]
    # FIXME: Group is deleted atm
    # TODO: we should check whether all attrs are persisted


@mock_aws
def test_create_database_in_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSubnetGroupName="db_subnet1",
    )
    result = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert result["DBInstances"][0]["DBSubnetGroup"]["DBSubnetGroupName"] == (
        "db_subnet1"
    )


def create_db_subnet_group(db_subnet_group_name: str = "custom_db_subnet") -> str:
    ec2 = boto3.client("ec2", region_name=DEFAULT_REGION)
    first_subnet_id = ec2.describe_subnets()["Subnets"][0]["SubnetId"]

    rds = boto3.client("rds", region_name=DEFAULT_REGION)
    rds.create_db_subnet_group(
        DBSubnetGroupName=db_subnet_group_name,
        DBSubnetGroupDescription="xxx",
        SubnetIds=[first_subnet_id],
    )
    return db_subnet_group_name


@mock_aws
def test_describe_database_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )
    client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet2",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )

    resp = client.describe_db_subnet_groups()
    assert len(resp["DBSubnetGroups"]) == 2

    subnets = resp["DBSubnetGroups"][0]["Subnets"]
    assert len(subnets) == 1

    assert (
        len(
            list(
                client.describe_db_subnet_groups(DBSubnetGroupName="db_subnet1")[
                    "DBSubnetGroups"
                ]
            )
        )
        == 1
    )

    with pytest.raises(ClientError):
        client.describe_db_subnet_groups(DBSubnetGroupName="not-a-subnet")


@mock_aws
def test_delete_database_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )
    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 1

    client.delete_db_subnet_group(DBSubnetGroupName="db_subnet1")
    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    with pytest.raises(ClientError):
        client.delete_db_subnet_group(DBSubnetGroupName="db_subnet1")


@mock_aws
def test_list_tags_database_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    subnet = client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    result = client.list_tags_for_resource(
        ResourceName=f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"
    )
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_modify_tags_parameter_group(client):
    client_tags = [{"Key": "character_set_client", "Value": "utf-8"}]
    result = client.create_db_parameter_group(
        DBParameterGroupName="test-sqlserver-2017",
        DBParameterGroupFamily="mysql5.6",
        Description="MySQL Group",
        Tags=client_tags,
    )
    resource = result["DBParameterGroup"]["DBParameterGroupArn"]
    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == client_tags
    server_tags = [{"Key": "character_set_server", "Value": "utf-8"}]
    client.add_tags_to_resource(ResourceName=resource, Tags=server_tags)
    combined_tags = client_tags + server_tags
    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == combined_tags

    client.remove_tags_from_resource(
        ResourceName=resource, TagKeys=["character_set_client"]
    )
    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == server_tags


@mock_aws
def test_modify_tags_event_subscription(client):
    tags = [{"Key": "hello", "Value": "world"}]
    result = client.create_event_subscription(
        SubscriptionName="my-instance-events",
        SourceType="db-instance",
        EventCategories=["backup", "recovery"],
        SnsTopicArn="arn:aws:sns:us-east-1:123456789012:interesting-events",
        Tags=tags,
    )
    resource = result["EventSubscription"]["EventSubscriptionArn"]
    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == tags
    new_tags = [{"Key": "new_key", "Value": "new_value"}]
    client.add_tags_to_resource(ResourceName=resource, Tags=new_tags)
    combined_tags = tags + new_tags
    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == combined_tags

    client.remove_tags_from_resource(ResourceName=resource, TagKeys=["new_key"])
    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == tags


@mock_aws
def test_add_tags_database_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    subnet = client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"

    client.add_tags_to_resource(
        ResourceName=resource,
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )

    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_remove_tags_database_subnet_group(client):
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    result = client.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    subnet = client.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"

    client.remove_tags_from_resource(ResourceName=resource, TagKeys=["foo"])

    result = client.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [{"Value": "bar1", "Key": "foo1"}]


@mock_aws
def test_create_database_replica(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    replica = client.create_db_instance_read_replica(
        DBInstanceIdentifier="db-replica-1",
        SourceDBInstanceIdentifier="db-master-1",
        DBInstanceClass="db.m1.small",
    )
    assert replica["DBInstance"]["ReadReplicaSourceDBInstanceIdentifier"] == (
        "db-master-1"
    )
    assert replica["DBInstance"]["DBInstanceClass"] == "db.m1.small"
    assert replica["DBInstance"]["DBInstanceIdentifier"] == "db-replica-1"

    master = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert master["DBInstances"][0]["ReadReplicaDBInstanceIdentifiers"] == (
        ["db-replica-1"]
    )
    replica = client.describe_db_instances(DBInstanceIdentifier="db-replica-1")[
        "DBInstances"
    ][0]
    assert replica["ReadReplicaSourceDBInstanceIdentifier"] == "db-master-1"

    client.delete_db_instance(
        DBInstanceIdentifier="db-replica-1", SkipFinalSnapshot=True
    )

    master = client.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert master["DBInstances"][0]["ReadReplicaDBInstanceIdentifiers"] == []


@mock_aws
def test_create_database_replica_cross_region():
    us1 = boto3.client("rds", region_name="us-east-1")
    us2 = boto3.client("rds", region_name=DEFAULT_REGION)

    source_id = "db-master-1"
    source_arn = us1.create_db_instance(
        DBInstanceIdentifier=source_id,
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
    )["DBInstance"]["DBInstanceArn"]

    target_id = "db-replica-1"
    target_arn = us2.create_db_instance_read_replica(
        DBInstanceIdentifier=target_id,
        SourceDBInstanceIdentifier=source_arn,
        DBInstanceClass="db.m1.small",
    )["DBInstance"]["DBInstanceArn"]

    source_db = us1.describe_db_instances(DBInstanceIdentifier=source_id)[
        "DBInstances"
    ][0]
    assert source_db["ReadReplicaDBInstanceIdentifiers"] == [target_arn]

    target_db = us2.describe_db_instances(DBInstanceIdentifier=target_id)[
        "DBInstances"
    ][0]
    assert target_db["ReadReplicaSourceDBInstanceIdentifier"] == source_arn


@mock_aws
def test_create_database_with_encrypted_storage(client):
    kms_conn = boto3.client("kms", region_name=DEFAULT_REGION)
    key = kms_conn.create_key(
        Policy="my RDS encryption policy",
        Description="RDS encryption key",
        KeyUsage="ENCRYPT_DECRYPT",
    )

    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        StorageEncrypted=True,
        KmsKeyId=key["KeyMetadata"]["KeyId"],
    )

    assert database["DBInstance"]["StorageEncrypted"] is True
    assert database["DBInstance"]["KmsKeyId"] == key["KeyMetadata"]["KeyId"]


@mock_aws
def test_create_db_parameter_group(client):
    pg_name = "test"
    db_parameter_group = client.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    assert db_parameter_group["DBParameterGroup"]["DBParameterGroupName"] == "test"
    assert db_parameter_group["DBParameterGroup"]["DBParameterGroupFamily"] == (
        "mysql5.6"
    )
    assert db_parameter_group["DBParameterGroup"]["Description"] == (
        "test parameter group"
    )
    assert db_parameter_group["DBParameterGroup"]["DBParameterGroupArn"] == (
        f"arn:aws:rds:{DEFAULT_REGION}:{ACCOUNT_ID}:pg:{pg_name}"
    )


@mock_aws
def test_create_db_instance_with_parameter_group(client):
    client.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="mysql",
        DBInstanceClass="db.m1.small",
        DBParameterGroupName="test",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    assert len(database["DBInstance"]["DBParameterGroups"]) == 1
    assert database["DBInstance"]["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "test"
    )
    assert database["DBInstance"]["DBParameterGroups"][0]["ParameterApplyStatus"] == (
        "in-sync"
    )


@mock_aws
def test_create_database_with_default_port(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        DBSecurityGroups=["my_sg"],
    )
    assert database["DBInstance"]["Endpoint"]["Port"] == 5432


@mock_aws
def test_modify_db_instance_with_parameter_group(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="mysql",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    assert len(database["DBInstance"]["DBParameterGroups"]) == 1
    assert database["DBInstance"]["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "default.mysql5.6"
    )
    assert database["DBInstance"]["DBParameterGroups"][0]["ParameterApplyStatus"] == (
        "in-sync"
    )

    client.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    client.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        DBParameterGroupName="test",
        ApplyImmediately=True,
    )

    database = client.describe_db_instances(DBInstanceIdentifier="db-master-1")[
        "DBInstances"
    ][0]
    assert len(database["DBParameterGroups"]) == 1
    assert database["DBParameterGroups"][0]["DBParameterGroupName"] == "test"
    assert database["DBParameterGroups"][0]["ParameterApplyStatus"] == "in-sync"


@mock_aws
def test_create_db_parameter_group_empty_description(client):
    with pytest.raises(ClientError):
        client.create_db_parameter_group(
            DBParameterGroupName="test",
            DBParameterGroupFamily="mysql5.6",
            Description="",
        )


@mock_aws
def test_create_db_parameter_group_duplicate(client):
    client.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    with pytest.raises(ClientError):
        client.create_db_parameter_group(
            DBParameterGroupName="test",
            DBParameterGroupFamily="mysql5.6",
            Description="test parameter group",
        )


@mock_aws
def test_describe_db_parameter_group(client):
    pg_name = "test"
    client.create_db_parameter_group(
        DBParameterGroupName=pg_name,
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = client.describe_db_parameter_groups(
        DBParameterGroupName="test"
    )
    assert db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "test"
    )
    assert db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupArn"] == (
        f"arn:aws:rds:{DEFAULT_REGION}:{ACCOUNT_ID}:pg:{pg_name}"
    )


@mock_aws
def test_describe_non_existent_db_parameter_group(client):
    db_parameter_groups = client.describe_db_parameter_groups(
        DBParameterGroupName="test"
    )
    assert len(db_parameter_groups["DBParameterGroups"]) == 0


@mock_aws
def test_delete_db_parameter_group(client):
    client.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = client.describe_db_parameter_groups(
        DBParameterGroupName="test"
    )
    assert db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "test"
    )
    client.delete_db_parameter_group(DBParameterGroupName="test")
    db_parameter_groups = client.describe_db_parameter_groups(
        DBParameterGroupName="test"
    )
    assert len(db_parameter_groups["DBParameterGroups"]) == 0


@mock_aws
def test_modify_db_parameter_group(client):
    client.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    modify_result = client.modify_db_parameter_group(
        DBParameterGroupName="test",
        Parameters=[
            {
                "ParameterName": "foo",
                "ParameterValue": "foo_val",
                "Description": "test param",
                "ApplyMethod": "immediate",
            }
        ],
    )

    assert modify_result["DBParameterGroupName"] == "test"

    db_parameters = client.describe_db_parameters(DBParameterGroupName="test")
    assert db_parameters["Parameters"][0]["ParameterName"] == "foo"
    assert db_parameters["Parameters"][0]["ParameterValue"] == "foo_val"
    assert db_parameters["Parameters"][0]["Description"] == "test param"
    assert db_parameters["Parameters"][0]["ApplyMethod"] == "immediate"


@mock_aws
def test_delete_non_existent_db_parameter_group(client):
    with pytest.raises(ClientError):
        client.delete_db_parameter_group(DBParameterGroupName="non-existent")


@mock_aws
def test_create_parameter_group_with_tags(client):
    client.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
        Tags=[{"Key": "foo", "Value": "bar"}],
    )
    result = client.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:pg:test"
    )
    assert result["TagList"] == [{"Value": "bar", "Key": "foo"}]


@mock_aws
def test_create_db_with_iam_authentication(client):
    database = client.create_db_instance(
        DBInstanceIdentifier="rds",
        DBInstanceClass="db.t1.micro",
        Engine="postgres",
        EnableIAMDatabaseAuthentication=True,
    )

    db_instance = database["DBInstance"]
    assert db_instance["IAMDatabaseAuthenticationEnabled"] is True

    snapshot = client.create_db_snapshot(
        DBInstanceIdentifier="rds", DBSnapshotIdentifier="snapshot"
    ).get("DBSnapshot")

    assert snapshot.get("IAMDatabaseAuthenticationEnabled") is True


@mock_aws
def test_create_db_instance_with_tags():
    client = boto3.client("rds", region_name=DEFAULT_REGION)
    tags = [{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}]
    db_instance_identifier = "test-db-instance"
    resp = client.create_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        Tags=tags,
    )
    assert resp["DBInstance"]["TagList"] == tags

    resp = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    assert resp["DBInstances"][0]["TagList"] == tags


@mock_aws
def test_create_db_instance_without_availability_zone():
    region = "us-east-1"
    client = boto3.client("rds", region_name=region)
    db_instance_identifier = "test-db-instance"
    resp = client.create_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
    )
    assert region in resp["DBInstance"]["AvailabilityZone"]

    resp = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    assert region in resp["DBInstances"][0]["AvailabilityZone"]


@mock_aws
def test_create_db_instance_with_availability_zone():
    region = "us-east-1"
    availability_zone = f"{region}c"
    client = boto3.client("rds", region_name=region)
    db_instance_identifier = "test-db-instance"
    resp = client.create_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        AvailabilityZone=availability_zone,
    )
    assert resp["DBInstance"]["AvailabilityZone"] == availability_zone

    resp = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    assert resp["DBInstances"][0]["AvailabilityZone"] == availability_zone


invalid_identifiers = ("-foo", "foo-", "2foo", "foo--bar", "", "foo_bar")
invalid_db_identifiers = invalid_identifiers + ("x" * 64,)
invalid_db_snapshot_identifiers = invalid_identifiers + ("x" * 256,)


@pytest.mark.parametrize("invalid_db_identifier", invalid_db_identifiers)
def test_validate_db_identifier_backend_invalid(invalid_db_identifier):
    with pytest.raises(InvalidDBInstanceIdentifier):
        RDSBackend._validate_db_identifier(invalid_db_identifier)


@pytest.mark.parametrize(
    "invalid_db_snapshot_identifier", invalid_db_snapshot_identifiers
)
def test_validate_db_snapshot_identifier_backend_invalid(
    invalid_db_snapshot_identifier,
):
    with pytest.raises(InvalidDBSnapshotIdentifier):
        RDSBackend.validate_db_snapshot_identifier(
            invalid_db_snapshot_identifier, "DBSnapshotIdentifier"
        )


valid_identifiers = ("f", "foo", "FOO", "FOO-bar-123")
valid_db_identifiers = valid_identifiers + ("x" * 63,)
valid_db_snapshot_identifiers = valid_identifiers + ("x" * 255,)


@pytest.mark.parametrize("valid_db_identifier", valid_db_identifiers)
def test_validate_db_identifier_backend_valid(valid_db_identifier):
    RDSBackend._validate_db_identifier(valid_db_identifier)


@pytest.mark.parametrize("valid_db_snapshot_identifier", valid_db_snapshot_identifiers)
def test_validate_db_snapshot_identifier_backend_valid(valid_db_snapshot_identifier):
    RDSBackend.validate_db_snapshot_identifier(
        valid_db_snapshot_identifier, "DBSnapshotIdentifier"
    )


@mock_aws
def test_validate_db_identifier():
    client = boto3.client("rds", region_name=DEFAULT_REGION)
    invalid_db_instance_identifier = "arn:aws:rds:eu-west-1:123456789012:db:mydb"

    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            DBInstanceIdentifier=invalid_db_instance_identifier,
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
        )
    validation_helper(exc)

    with pytest.raises(ClientError) as exc:
        client.start_db_instance(
            DBInstanceIdentifier=invalid_db_instance_identifier,
        )
    validation_helper(exc)

    with pytest.raises(ClientError) as exc:
        client.stop_db_instance(
            DBInstanceIdentifier=invalid_db_instance_identifier,
        )
    validation_helper(exc)

    with pytest.raises(ClientError) as exc:
        client.delete_db_instance(
            DBInstanceIdentifier=invalid_db_instance_identifier,
        )
    validation_helper(exc)

    with pytest.raises(ClientError) as exc:
        client.delete_db_instance(
            DBInstanceIdentifier="valid-1-id" * 10,
        )
    validation_helper(exc)


@mock_aws
def test_validate_db_snapshot_identifier_different_operations():
    client = boto3.client("rds", region_name=DEFAULT_REGION)
    db_instance_identifier = "valid-identifier"
    valid_db_snapshot_identifier = "valid"
    invalid_db_snapshot_identifier = "--invalid--"

    client.create_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
    )

    expected_message = f"Invalid snapshot identifier:  {invalid_db_snapshot_identifier}"
    with pytest.raises(ClientError) as exc:
        client.create_db_snapshot(
            DBSnapshotIdentifier=invalid_db_snapshot_identifier,
            DBInstanceIdentifier=db_instance_identifier,
        )
    snapshot_validation_helper(exc, expected_message)

    client.create_db_snapshot(
        DBSnapshotIdentifier=valid_db_snapshot_identifier,
        DBInstanceIdentifier=db_instance_identifier,
    )

    with pytest.raises(ClientError) as exc:
        client.copy_db_snapshot(
            SourceDBSnapshotIdentifier=valid_db_snapshot_identifier,
            TargetDBSnapshotIdentifier=invalid_db_snapshot_identifier,
        )
    snapshot_validation_helper(exc, expected_message)

    with pytest.raises(ClientError) as exc:
        client.stop_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            DBSnapshotIdentifier=invalid_db_snapshot_identifier,
        )
    snapshot_validation_helper(exc, expected_message)

    with pytest.raises(ClientError) as exc:
        client.delete_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            FinalDBSnapshotIdentifier=invalid_db_snapshot_identifier,
        )
    snapshot_validation_helper(exc, expected_message)


# Depending on what is wrong with the snapshot_identifier, AWS produces different error messages.
snapshot_identifier_data = (
    ("", "The parameter DBSnapshotIdentifier must be provided and must not be blank."),
    ("-invalid", "Invalid snapshot identifier:  -invalid"),
    (
        "in--valid",
        (
            "The parameter DBSnapshotIdentifier is not a valid identifier. "
            "Identifiers must begin with a letter; must contain only ASCII "
            "letters, digits, and hyphens; and must not end with a hyphen "
            "or contain two consecutive hyphens."
        ),
    ),
)


@pytest.mark.parametrize(
    "invalid_db_snapshot_identifier,expected_message",
    snapshot_identifier_data,
    ids=("empty", "invalid_first_character", "default_message"),
)
@mock_aws
def test_validate_db_snapshot_identifier_different_error_messages(
    invalid_db_snapshot_identifier, expected_message, client
):
    db_instance_identifier = "valid-identifier"
    client.create_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
    )

    with pytest.raises(ClientError) as exc:
        client.create_db_snapshot(
            DBSnapshotIdentifier=invalid_db_snapshot_identifier,
            DBInstanceIdentifier=db_instance_identifier,
        )
    snapshot_validation_helper(exc, expected_message)


@mock_aws
def test_createdb_instance_engine_with_invalid_value(client):
    with pytest.raises(ClientError) as exc:
        client.create_db_instance(
            DBInstanceIdentifier="test-db-instance",
            Engine="invalid-engine",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
        )

    err = exc.value.response["Error"]

    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "Value invalid-engine for parameter Engine is invalid. Reason: engine invalid-engine not supported"
    )


@mock_aws
def test_describe_db_snapshot_attributes_default(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshot")

    resp = client.describe_db_snapshot_attributes(DBSnapshotIdentifier="snapshot-1")

    assert resp["DBSnapshotAttributesResult"]["DBSnapshotIdentifier"] == "snapshot-1"
    assert resp["DBSnapshotAttributesResult"]["DBSnapshotAttributes"] == []


@mock_aws
def test_describe_db_snapshot_attributes(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshot")

    resp = client.modify_db_snapshot_attribute(
        DBSnapshotIdentifier="snapshot-1",
        AttributeName="restore",
        ValuesToAdd=["Test", "Test2"],
    )

    resp = client.describe_db_snapshot_attributes(DBSnapshotIdentifier="snapshot-1")

    assert (
        resp["DBSnapshotAttributesResult"]["DBSnapshotAttributes"][0]["AttributeName"]
        == "restore"
    )
    assert resp["DBSnapshotAttributesResult"]["DBSnapshotAttributes"][0][
        "AttributeValues"
    ] == ["Test", "Test2"]


@mock_aws
def test_modify_db_snapshot_attribute(client):
    client.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    client.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshot")

    resp = client.modify_db_snapshot_attribute(
        DBSnapshotIdentifier="snapshot-1",
        AttributeName="restore",
        ValuesToAdd=["Test", "Test2"],
    )
    resp = client.modify_db_snapshot_attribute(
        DBSnapshotIdentifier="snapshot-1",
        AttributeName="restore",
        ValuesToRemove=["Test"],
    )
    resp = client.modify_db_snapshot_attribute(
        DBSnapshotIdentifier="snapshot-1",
        AttributeName="restore",
        ValuesToAdd=["Test3"],
    )

    assert (
        resp["DBSnapshotAttributesResult"]["DBSnapshotAttributes"][0]["AttributeName"]
        == "restore"
    )
    assert resp["DBSnapshotAttributesResult"]["DBSnapshotAttributes"][0][
        "AttributeValues"
    ] == ["Test2", "Test3"]


def validation_helper(exc):
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter DBInstanceIdentifier is not a valid identifier. "
        "Identifiers must begin with a letter; must contain only ASCII "
        "letters, digits, and hyphens; "
        "and must not end with a hyphen or contain two consecutive hyphens."
    )


def snapshot_validation_helper(exc, expected_message):
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == expected_message
