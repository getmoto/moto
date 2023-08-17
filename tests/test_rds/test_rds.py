import datetime

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_ec2, mock_kms, mock_rds
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

DEFAULT_REGION = "us-west-2"


@mock_rds
def test_create_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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


@mock_rds
def test_database_with_deletion_protection_cannot_be_deleted():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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


@mock_rds
def test_create_database_no_allocated_storage():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_more_24_hours():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16:00-tue:17:00",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Maintenance window must be less than 24 hours."


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_less_30_mins():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16:00-mon:16:05",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "The maintenance window must be at least 30 minutes."


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_value():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="sim:16:00-mon:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert "Invalid day:hour:minute" in err["Message"]


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_format():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
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


@mock_rds
def test_create_database_preferred_backup_window_overlap_no_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
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


@mock_rds
def test_create_database_preferred_backup_window_overlap_maintenance_window_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
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


@mock_rds
def test_create_database_preferred_backup_window_overlap_backup_window_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
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


@mock_rds
def test_create_database_preferred_backup_window_overlap_both_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
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


@mock_rds
def test_create_database_valid_preferred_maintenance_window_format():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        PreferredMaintenanceWindow="sun:16:00-sun:16:30",
    )
    db_instance = database["DBInstance"]
    assert db_instance["DBInstanceClass"] == "db.m1.small"
    assert db_instance["PreferredMaintenanceWindow"] == "sun:16:00-sun:16:30"


@mock_rds
def test_create_database_valid_preferred_maintenance_window_uppercase_format():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        PreferredMaintenanceWindow="MON:16:00-TUE:01:30",
    )
    db_instance = database["DBInstance"]
    assert db_instance["DBInstanceClass"] == "db.m1.small"
    assert db_instance["PreferredMaintenanceWindow"] == "mon:16:00-tue:01:30"


@mock_rds
def test_create_database_non_existing_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            AllocatedStorage=10,
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            OptionGroupName="non-existing",
        )


@mock_rds
def test_create_database_with_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="my-og",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    database = conn.create_db_instance(
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


@mock_rds
def test_stop_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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
    mydb = conn.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # test stopping database should shutdown
    response = conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"
    # test rdsclient error when trying to stop an already stopped database
    with pytest.raises(ClientError):
        conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # test stopping a stopped database with snapshot should error and no
    # snapshot should exist for that call
    with pytest.raises(ClientError):
        conn.stop_db_instance(
            DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
            DBSnapshotIdentifier="rocky4570-rds-snap",
        )
    response = conn.describe_db_snapshots()
    assert response["DBSnapshots"] == []


@mock_rds
def test_start_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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
    mydb = conn.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # test starting an already started database should error
    with pytest.raises(ClientError):
        conn.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # stop and test start - should go from stopped to available, create
    # snapshot and check snapshot
    response = conn.stop_db_instance(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
        DBSnapshotIdentifier="rocky4570-rds-snap",
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"
    response = conn.describe_db_snapshots()
    assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "rocky4570-rds-snap"
    response = conn.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "available"
    # starting database should not remove snapshot
    response = conn.describe_db_snapshots()
    assert response["DBSnapshots"][0]["DBSnapshotIdentifier"] == "rocky4570-rds-snap"
    # test stopping database, create snapshot with existing snapshot already
    # created should throw error
    with pytest.raises(ClientError):
        conn.stop_db_instance(
            DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
            DBSnapshotIdentifier="rocky4570-rds-snap",
        )
    # test stopping database not invoking snapshot should succeed.
    response = conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"


@mock_rds
def test_fail_to_stop_multi_az_and_sqlserver():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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

    mydb = conn.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # multi-az databases arent allowed to be shutdown at this time.
    with pytest.raises(ClientError):
        conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # multi-az databases arent allowed to be started up at this time.
    with pytest.raises(ClientError):
        conn.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])


@mock_rds
def test_stop_multi_az_postgres():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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

    mydb = conn.describe_db_instances(
        DBInstanceIdentifier=database["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"

    response = conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert response["DBInstance"]["DBInstanceStatus"] == "stopped"


@mock_rds
def test_fail_to_stop_readreplica():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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

    replica = conn.create_db_instance_read_replica(
        DBInstanceIdentifier="db-replica-1",
        SourceDBInstanceIdentifier="db-master-1",
        DBInstanceClass="db.m1.small",
    )

    mydb = conn.describe_db_instances(
        DBInstanceIdentifier=replica["DBInstance"]["DBInstanceIdentifier"]
    )["DBInstances"][0]
    assert mydb["DBInstanceStatus"] == "available"
    # read-replicas are not allowed to be stopped at this time.
    with pytest.raises(ClientError):
        conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    # read-replicas are not allowed to be started at this time.
    with pytest.raises(ClientError):
        conn.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])


@mock_rds
def test_get_databases():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    instances = conn.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 0

    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-2",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        DeletionProtection=True,
    )
    instances = conn.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 2

    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert len(list(instances["DBInstances"])) == 1
    assert instances["DBInstances"][0]["DBInstanceIdentifier"] == "db-master-1"
    assert instances["DBInstances"][0]["DeletionProtection"] is False
    assert instances["DBInstances"][0]["DBInstanceArn"] == (
        f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:db:db-master-1"
    )

    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-2")
    assert instances["DBInstances"][0]["DeletionProtection"] is True
    assert instances["DBInstances"][0]["Endpoint"]["Port"] == 1234
    assert instances["DBInstances"][0]["DbInstancePort"] == 1234


@mock_rds
def test_get_databases_paginated():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    for i in range(51):
        conn.create_db_instance(
            AllocatedStorage=5,
            Port=5432,
            DBInstanceIdentifier=f"rds{i}",
            DBInstanceClass="db.t1.micro",
            Engine="postgres",
        )

    resp = conn.describe_db_instances()
    assert len(resp["DBInstances"]) == 50
    assert resp["Marker"] == resp["DBInstances"][-1]["DBInstanceIdentifier"]

    resp2 = conn.describe_db_instances(Marker=resp["Marker"])
    assert len(resp2["DBInstances"]) == 1

    resp3 = conn.describe_db_instances(MaxRecords=100)
    assert len(resp3["DBInstances"]) == 51


@mock_rds
def test_describe_non_existent_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.describe_db_instances(DBInstanceIdentifier="not-a-db")


@mock_rds
def test_modify_db_instance():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["AllocatedStorage"] == 10
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=20,
        ApplyImmediately=True,
        VpcSecurityGroupIds=["sg-123456"],
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["AllocatedStorage"] == 20
    assert instances["DBInstances"][0]["PreferredMaintenanceWindow"] == (
        "wed:06:38-wed:07:08"
    )
    assert (
        instances["DBInstances"][0]["VpcSecurityGroups"][0]["VpcSecurityGroupId"]
        == "sg-123456"
    )


@mock_rds
def test_modify_db_instance_not_existent_db_parameter_group_name():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["AllocatedStorage"] == 10
    with pytest.raises(ClientError):
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            DBParameterGroupName="test-sqlserver-se-2017",
        )


@mock_rds
def test_modify_db_instance_valid_preferred_maintenance_window():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        PreferredMaintenanceWindow="sun:16:00-sun:16:30",
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["PreferredMaintenanceWindow"] == (
        "sun:16:00-sun:16:30"
    )


@mock_rds
def test_modify_db_instance_valid_preferred_maintenance_window_uppercase():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        PreferredMaintenanceWindow="SUN:16:00-SUN:16:30",
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert instances["DBInstances"][0]["PreferredMaintenanceWindow"] == (
        "sun:16:00-sun:16:30"
    )


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_more_than_24_hours():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-sat:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Maintenance window must be less than 24 hours."


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_less_than_30_mins():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-sun:16:10",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "The maintenance window must be at least 30 minutes."


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_value():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sin:16:00-sun:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert "Invalid day:hour:minute value" in err["Message"]


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_format():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00sun:16:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        "Should be specified as a range ddd:hh24:mi-ddd:hh24:mi "
        "(24H Clock UTC). Example: Sun:23:45-Mon:00:15"
    ) in err["Message"]


@mock_rds
def test_modify_db_instance_maintenance_backup_window_no_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-sun:16:30",
            PreferredBackupWindow="15:50-16:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"] == "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_modify_db_instance_maintenance_backup_window_maintenance_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-mon:15:00",
            PreferredBackupWindow="00:00-00:30",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_modify_db_instance_maintenance_backup_window_backup_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="mon:00:00-mon:15:00",
            PreferredBackupWindow="23:50-00:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_modify_db_instance_maintenance_backup_window_both_spill():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    with pytest.raises(ClientError) as ex:
        conn.modify_db_instance(
            DBInstanceIdentifier="db-master-1",
            PreferredMaintenanceWindow="sun:16:00-mon:15:00",
            PreferredBackupWindow="23:20-00:20",
        )
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_rename_db_instance():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert len(list(instances["DBInstances"])) == 1
    with pytest.raises(ClientError):
        conn.describe_db_instances(DBInstanceIdentifier="db-master-2")
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        NewDBInstanceIdentifier="db-master-2",
        ApplyImmediately=True,
    )
    with pytest.raises(ClientError):
        conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-2")
    assert len(list(instances["DBInstances"])) == 1


@mock_rds
def test_modify_non_existent_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.modify_db_instance(
            DBInstanceIdentifier="not-a-db", AllocatedStorage=20, ApplyImmediately=True
        )


@mock_rds
def test_reboot_db_instance():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    database = conn.reboot_db_instance(DBInstanceIdentifier="db-master-1")
    assert database["DBInstance"]["DBInstanceIdentifier"] == "db-master-1"


@mock_rds
def test_reboot_non_existent_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.reboot_db_instance(DBInstanceIdentifier="not-a-db")


@mock_rds
def test_delete_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    instances = conn.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 0
    conn.create_db_instance(
        DBInstanceIdentifier="db-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = conn.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 1

    conn.delete_db_instance(
        DBInstanceIdentifier="db-1",
        FinalDBSnapshotIdentifier="primary-1-snapshot",
    )

    instances = conn.describe_db_instances()
    assert len(list(instances["DBInstances"])) == 0

    # Saved the snapshot
    snapshot = conn.describe_db_snapshots(DBInstanceIdentifier="db-1")["DBSnapshots"][0]
    assert snapshot["Engine"] == "postgres"
    assert snapshot["SnapshotType"] == "automated"


@mock_rds
def test_create_db_snapshots():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.create_db_snapshot(
            DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
        )

    conn.create_db_instance(
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

    snapshot = conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="g-1"
    ).get("DBSnapshot")

    assert snapshot.get("Engine") == "postgres"
    assert snapshot.get("DBInstanceIdentifier") == "db-primary-1"
    assert snapshot.get("DBSnapshotIdentifier") == "g-1"
    result = conn.list_tags_for_resource(ResourceName=snapshot["DBSnapshotArn"])
    assert result["TagList"] == []


@mock_rds
def test_create_db_snapshots_copy_tags():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.create_db_snapshot(
            DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
        )

    conn.create_db_instance(
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

    snapshot = conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="g-1"
    ).get("DBSnapshot")

    assert snapshot.get("Engine") == "postgres"
    assert snapshot.get("DBInstanceIdentifier") == "db-primary-1"
    assert snapshot.get("DBSnapshotIdentifier") == "g-1"
    result = conn.list_tags_for_resource(ResourceName=snapshot["DBSnapshotArn"])
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_rds
def test_create_db_snapshots_with_tags():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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

    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="g-1",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )

    snapshots = conn.describe_db_snapshots(DBInstanceIdentifier="db-primary-1").get(
        "DBSnapshots"
    )
    assert snapshots[0].get("DBSnapshotIdentifier") == "g-1"
    assert snapshots[0].get("TagList") == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_rds
def test_copy_db_snapshots():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    conn.create_db_instance(
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

    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshot")

    target_snapshot = conn.copy_db_snapshot(
        SourceDBSnapshotIdentifier="snapshot-1", TargetDBSnapshotIdentifier="snapshot-2"
    ).get("DBSnapshot")

    assert target_snapshot.get("Engine") == "postgres"
    assert target_snapshot.get("DBInstanceIdentifier") == "db-primary-1"
    assert target_snapshot.get("DBSnapshotIdentifier") == "snapshot-2"
    result = conn.list_tags_for_resource(ResourceName=target_snapshot["DBSnapshotArn"])
    assert result["TagList"] == []


@mock_rds
def test_describe_db_snapshots():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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

    created = conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).get("DBSnapshot")

    assert created["Engine"] == "postgres"
    assert created["SnapshotType"] == "manual"

    by_database_id = conn.describe_db_snapshots(
        DBInstanceIdentifier="db-primary-1"
    ).get("DBSnapshots")
    by_snapshot_id = conn.describe_db_snapshots(DBSnapshotIdentifier="snapshot-1").get(
        "DBSnapshots"
    )
    assert by_snapshot_id == by_database_id

    snapshot = by_snapshot_id[0]
    assert snapshot == created

    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-2"
    )
    snapshots = conn.describe_db_snapshots(DBInstanceIdentifier="db-primary-1").get(
        "DBSnapshots"
    )
    assert len(snapshots) == 2


@mock_rds
def test_promote_read_replica():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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

    conn.create_db_instance_read_replica(
        DBInstanceIdentifier="db-replica-1",
        SourceDBInstanceIdentifier="db-primary-1",
        DBInstanceClass="db.m1.small",
    )
    conn.promote_read_replica(DBInstanceIdentifier="db-replica-1")

    replicas = conn.describe_db_instances(DBInstanceIdentifier="db-primary-1").get(
        "ReadReplicaDBInstanceIdentifiers"
    )
    assert replicas is None


@mock_rds
def test_delete_db_snapshot():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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
    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    )

    _ = conn.describe_db_snapshots(DBSnapshotIdentifier="snapshot-1").get(
        "DBSnapshots"
    )[0]
    conn.delete_db_snapshot(DBSnapshotIdentifier="snapshot-1")
    with pytest.raises(ClientError):
        conn.describe_db_snapshots(DBSnapshotIdentifier="snapshot-1")


@mock_rds
def test_restore_db_instance_from_db_snapshot():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        DBSecurityGroups=["my_sg"],
    )
    assert len(conn.describe_db_instances()["DBInstances"]) == 1

    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    )

    # restore
    new_instance = conn.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier="db-restore-1", DBSnapshotIdentifier="snapshot-1"
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
    assert len(conn.describe_db_instances()["DBInstances"]) == 2
    assert (
        len(
            conn.describe_db_instances(DBInstanceIdentifier="db-restore-1")[
                "DBInstances"
            ]
        )
        == 1
    )


@mock_rds
def test_restore_db_instance_from_db_snapshot_and_override_params():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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
    assert len(conn.describe_db_instances()["DBInstances"]) == 1
    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    )

    # restore with some updated attributes
    new_instance = conn.restore_db_instance_from_db_snapshot(
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


@mock_rds
def test_create_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    option_group = conn.create_option_group(
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


@mock_rds
def test_create_option_group_bad_engine_name():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.create_option_group(
            OptionGroupName="test",
            EngineName="invalid_engine",
            MajorEngineVersion="5.6",
            OptionGroupDescription="test invalid engine",
        )


@mock_rds
def test_create_option_group_bad_engine_major_version():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.create_option_group(
            OptionGroupName="test",
            EngineName="mysql",
            MajorEngineVersion="6.6.6",
            OptionGroupDescription="test invalid engine version",
        )


@mock_rds
def test_create_option_group_empty_description():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.create_option_group(
            OptionGroupName="test",
            EngineName="mysql",
            MajorEngineVersion="5.6",
            OptionGroupDescription="",
        )


@mock_rds
def test_create_option_group_duplicate():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    with pytest.raises(ClientError):
        conn.create_option_group(
            OptionGroupName="test",
            EngineName="mysql",
            MajorEngineVersion="5.6",
            OptionGroupDescription="test option group",
        )


@mock_rds
def test_describe_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = conn.describe_option_groups(OptionGroupName="test")
    assert option_groups["OptionGroupsList"][0]["OptionGroupName"] == "test"


@mock_rds
def test_describe_non_existent_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.describe_option_groups(OptionGroupName="not-a-option-group")


@mock_rds
def test_delete_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = conn.describe_option_groups(OptionGroupName="test")
    assert option_groups["OptionGroupsList"][0]["OptionGroupName"] == "test"
    conn.delete_option_group(OptionGroupName="test")
    with pytest.raises(ClientError):
        conn.describe_option_groups(OptionGroupName="test")


@mock_rds
def test_delete_non_existent_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.delete_option_group(OptionGroupName="non-existent")


@mock_rds
def test_describe_option_group_options():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    option_group_options = conn.describe_option_group_options(EngineName="sqlserver-ee")
    assert len(option_group_options["OptionGroupOptions"]) == 4
    option_group_options = conn.describe_option_group_options(
        EngineName="sqlserver-ee", MajorEngineVersion="11.00"
    )
    assert len(option_group_options["OptionGroupOptions"]) == 2
    option_group_options = conn.describe_option_group_options(
        EngineName="mysql", MajorEngineVersion="5.6"
    )
    assert len(option_group_options["OptionGroupOptions"]) == 1
    with pytest.raises(ClientError):
        conn.describe_option_group_options(EngineName="non-existent")
    with pytest.raises(ClientError):
        conn.describe_option_group_options(
            EngineName="mysql", MajorEngineVersion="non-existent"
        )


@mock_rds
def test_modify_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    # TODO: create option and validate before deleting.
    # if Someone can tell me how the hell to use this function
    # to add options to an option_group, I can finish coding this.
    result = conn.modify_option_group(
        OptionGroupName="test",
        OptionsToInclude=[],
        OptionsToRemove=["MEMCACHED"],
        ApplyImmediately=True,
    )
    assert result["OptionGroup"]["EngineName"] == "mysql"
    assert result["OptionGroup"]["Options"] == []
    assert result["OptionGroup"]["OptionGroupName"] == "test"


@mock_rds
def test_modify_option_group_no_options():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    with pytest.raises(ClientError):
        conn.modify_option_group(OptionGroupName="test")


@mock_rds
def test_modify_non_existent_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as client_err:
        conn.modify_option_group(
            OptionGroupName="non-existent",
            OptionsToInclude=[{"OptionName": "test-option"}],
        )
    assert client_err.value.response["Error"]["Message"] == (
        "Specified OptionGroupName: non-existent not found."
    )


@mock_rds
def test_delete_database_with_protection():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        DeletionProtection=True,
    )

    with pytest.raises(ClientError) as exc:
        conn.delete_db_instance(DBInstanceIdentifier="db-primary-1")
    err = exc.value.response["Error"]
    assert err["Message"] == "Can't delete Instance with protection enabled"


@mock_rds
def test_delete_non_existent_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as ex:
        conn.delete_db_instance(DBInstanceIdentifier="non-existent")
    assert ex.value.response["Error"]["Code"] == "DBInstanceNotFound"
    assert ex.value.response["Error"]["Message"] == "DBInstance non-existent not found."


@mock_rds
def test_list_tags_invalid_arn():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.list_tags_for_resource(ResourceName="arn:aws:rds:bad-arn")


@mock_rds
def test_list_tags_db():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:foo"
    )
    assert result["TagList"] == []
    test_instance = conn.create_db_instance(
        DBInstanceIdentifier="db-with-tags",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName=test_instance["DBInstance"]["DBInstanceArn"]
    )
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_rds
def test_add_tags_db():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-without-tags",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags"
    )
    assert len(list(result["TagList"])) == 2
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags"
    )
    assert len(list(result["TagList"])) == 3


@mock_rds
def test_remove_tags_db():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
        DBInstanceIdentifier="db-with-tags",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags"
    )
    assert len(list(result["TagList"])) == 2
    conn.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags", TagKeys=["foo"]
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags"
    )
    assert len(result["TagList"]) == 1


@mock_rds
def test_list_tags_snapshot():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:foo"
    )
    assert result["TagList"] == []
    conn.create_db_instance(
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
    snapshot = conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="snapshot-with-tags",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName=snapshot["DBSnapshot"]["DBSnapshotArn"]
    )
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_rds
def test_add_tags_snapshot():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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
    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="snapshot-without-tags",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags"
    )
    assert len(list(result["TagList"])) == 2
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags"
    )
    assert len(list(result["TagList"])) == 3


@mock_rds
def test_remove_tags_snapshot():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_instance(
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
    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1",
        DBSnapshotIdentifier="snapshot-with-tags",
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags"
    )
    assert len(list(result["TagList"])) == 2
    conn.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags",
        TagKeys=["foo"],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags"
    )
    assert len(result["TagList"]) == 1


@mock_rds
def test_add_tags_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 0
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 2


@mock_rds
def test_remove_tags_option_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 2
    conn.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test", TagKeys=["foo"]
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    assert len(list(result["TagList"])) == 1


@mock_rds
def test_create_database_security_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    result = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    assert result["DBSecurityGroup"]["DBSecurityGroupName"] == "db_sg"
    assert (
        result["DBSecurityGroup"]["DBSecurityGroupDescription"] == "DB Security Group"
    )
    assert result["DBSecurityGroup"]["IPRanges"] == []


@mock_rds
def test_get_security_groups():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    result = conn.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 0

    conn.create_db_security_group(
        DBSecurityGroupName="db_sg1", DBSecurityGroupDescription="DB Security Group"
    )
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg2", DBSecurityGroupDescription="DB Security Group"
    )

    result = conn.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 2

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg1")
    assert len(result["DBSecurityGroups"]) == 1
    assert result["DBSecurityGroups"][0]["DBSecurityGroupName"] == "db_sg1"


@mock_rds
def test_get_non_existent_security_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.describe_db_security_groups(DBSecurityGroupName="not-a-sg")


@mock_rds
def test_delete_database_security_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )

    result = conn.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 1

    conn.delete_db_security_group(DBSecurityGroupName="db_sg")
    result = conn.describe_db_security_groups()
    assert len(result["DBSecurityGroups"]) == 0


@mock_rds
def test_delete_non_existent_security_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.delete_db_security_group(DBSecurityGroupName="not-a-db")


@mock_rds
def test_security_group_authorize():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    assert security_group["DBSecurityGroup"]["IPRanges"] == []

    conn.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.45/32"
    )

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    assert len(result["DBSecurityGroups"][0]["IPRanges"]) == 1
    assert result["DBSecurityGroups"][0]["IPRanges"] == [
        {"Status": "authorized", "CIDRIP": "10.3.2.45/32"}
    ]

    conn.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.46/32"
    )
    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    assert len(result["DBSecurityGroups"][0]["IPRanges"]) == 2
    assert result["DBSecurityGroups"][0]["IPRanges"] == [
        {"Status": "authorized", "CIDRIP": "10.3.2.45/32"},
        {"Status": "authorized", "CIDRIP": "10.3.2.46/32"},
    ]


@mock_rds
def test_add_security_group_to_database():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        DBInstanceClass="postgres",
        Engine="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    result = conn.describe_db_instances()
    assert result["DBInstances"][0]["DBSecurityGroups"] == []
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1", DBSecurityGroups=["db_sg"]
    )
    result = conn.describe_db_instances()
    assert (
        result["DBInstances"][0]["DBSecurityGroups"][0]["DBSecurityGroupName"]
        == "db_sg"
    )


@mock_rds
def test_list_tags_security_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSecurityGroup"]["DBSecurityGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_rds
def test_add_tags_security_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    conn.add_tags_to_resource(
        ResourceName=resource,
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )

    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_rds
def test_remove_tags_security_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=["foo"])

    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [{"Value": "bar1", "Key": "foo1"}]


@mock_ec2
@mock_rds
def test_create_database_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]
    subnet2 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.2.0/24")[
        "Subnet"
    ]

    subnet_ids = [subnet1["SubnetId"], subnet2["SubnetId"]]
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=subnet_ids,
    )
    assert result["DBSubnetGroup"]["DBSubnetGroupName"] == "db_subnet"
    assert result["DBSubnetGroup"]["DBSubnetGroupDescription"] == "my db subnet"
    subnets = result["DBSubnetGroup"]["Subnets"]
    subnet_group_ids = [subnets[0]["SubnetIdentifier"], subnets[1]["SubnetIdentifier"]]
    assert list(subnet_group_ids) == subnet_ids


@mock_ec2
@mock_rds
def test_modify_database_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]
    subnet2 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.2.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet1["SubnetId"]],
    )

    conn.modify_db_subnet_group(
        DBSubnetGroupName="db_subnet",
        DBSubnetGroupDescription="my updated desc",
        SubnetIds=[subnet1["SubnetId"], subnet2["SubnetId"]],
    )

    _ = conn.describe_db_subnet_groups()["DBSubnetGroups"]
    # FIXME: Group is deleted atm
    # TODO: we should check whether all attrs are persisted


@mock_ec2
@mock_rds
def test_create_database_in_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )
    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSubnetGroupName="db_subnet1",
    )
    result = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert result["DBInstances"][0]["DBSubnetGroup"]["DBSubnetGroupName"] == (
        "db_subnet1"
    )


@mock_ec2
@mock_rds
def test_describe_database_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )
    conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet2",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )

    resp = conn.describe_db_subnet_groups()
    assert len(resp["DBSubnetGroups"]) == 2

    subnets = resp["DBSubnetGroups"][0]["Subnets"]
    assert len(subnets) == 1

    assert (
        len(
            list(
                conn.describe_db_subnet_groups(DBSubnetGroupName="db_subnet1")[
                    "DBSubnetGroups"
                ]
            )
        )
        == 1
    )

    with pytest.raises(ClientError):
        conn.describe_db_subnet_groups(DBSubnetGroupName="not-a-subnet")


@mock_ec2
@mock_rds
def test_delete_database_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 1

    conn.delete_db_subnet_group(DBSubnetGroupName="db_subnet1")
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    with pytest.raises(ClientError):
        conn.delete_db_subnet_group(DBSubnetGroupName="db_subnet1")


@mock_ec2
@mock_rds
def test_list_tags_database_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    subnet = conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    result = conn.list_tags_for_resource(
        ResourceName=f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"
    )
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_rds
def test_modify_tags_parameter_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    client_tags = [{"Key": "character_set_client", "Value": "utf-8"}]
    result = conn.create_db_parameter_group(
        DBParameterGroupName="test-sqlserver-2017",
        DBParameterGroupFamily="mysql5.6",
        Description="MySQL Group",
        Tags=client_tags,
    )
    resource = result["DBParameterGroup"]["DBParameterGroupArn"]
    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == client_tags
    server_tags = [{"Key": "character_set_server", "Value": "utf-8"}]
    conn.add_tags_to_resource(ResourceName=resource, Tags=server_tags)
    combined_tags = client_tags + server_tags
    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == combined_tags

    conn.remove_tags_from_resource(
        ResourceName=resource, TagKeys=["character_set_client"]
    )
    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == server_tags


@mock_rds
def test_modify_tags_event_subscription():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    tags = [{"Key": "hello", "Value": "world"}]
    result = conn.create_event_subscription(
        SubscriptionName="my-instance-events",
        SourceType="db-instance",
        EventCategories=["backup", "recovery"],
        SnsTopicArn="arn:aws:sns:us-east-1:123456789012:interesting-events",
        Tags=tags,
    )
    resource = result["EventSubscription"]["EventSubscriptionArn"]
    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == tags
    new_tags = [{"Key": "new_key", "Value": "new_value"}]
    conn.add_tags_to_resource(ResourceName=resource, Tags=new_tags)
    combined_tags = tags + new_tags
    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == combined_tags

    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=["new_key"])
    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == tags


@mock_ec2
@mock_rds
def test_add_tags_database_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    subnet = conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"

    conn.add_tags_to_resource(
        ResourceName=resource,
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )

    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_ec2
@mock_rds
def test_remove_tags_database_subnet_group():
    vpc_conn = boto3.client("ec2", DEFAULT_REGION)
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    result = conn.describe_db_subnet_groups()
    assert len(result["DBSubnetGroups"]) == 0

    subnet = conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"

    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=["foo"])

    result = conn.list_tags_for_resource(ResourceName=resource)
    assert result["TagList"] == [{"Value": "bar1", "Key": "foo1"}]


@mock_rds
def test_create_database_replica():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )

    replica = conn.create_db_instance_read_replica(
        DBInstanceIdentifier="db-replica-1",
        SourceDBInstanceIdentifier="db-master-1",
        DBInstanceClass="db.m1.small",
    )
    assert replica["DBInstance"]["ReadReplicaSourceDBInstanceIdentifier"] == (
        "db-master-1"
    )
    assert replica["DBInstance"]["DBInstanceClass"] == "db.m1.small"
    assert replica["DBInstance"]["DBInstanceIdentifier"] == "db-replica-1"

    master = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert master["DBInstances"][0]["ReadReplicaDBInstanceIdentifiers"] == (
        ["db-replica-1"]
    )
    replica = conn.describe_db_instances(DBInstanceIdentifier="db-replica-1")[
        "DBInstances"
    ][0]
    assert replica["ReadReplicaSourceDBInstanceIdentifier"] == "db-master-1"

    conn.delete_db_instance(DBInstanceIdentifier="db-replica-1", SkipFinalSnapshot=True)

    master = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    assert master["DBInstances"][0]["ReadReplicaDBInstanceIdentifiers"] == []


@mock_rds
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


@mock_rds
@mock_kms
def test_create_database_with_encrypted_storage():
    kms_conn = boto3.client("kms", region_name=DEFAULT_REGION)
    key = kms_conn.create_key(
        Policy="my RDS encryption policy",
        Description="RDS encryption key",
        KeyUsage="ENCRYPT_DECRYPT",
    )

    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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


@mock_rds
def test_create_db_parameter_group():
    region = DEFAULT_REGION
    pg_name = "test"
    conn = boto3.client("rds", region_name=region)
    db_parameter_group = conn.create_db_parameter_group(
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
        f"arn:aws:rds:{region}:{ACCOUNT_ID}:pg:{pg_name}"
    )


@mock_rds
def test_create_db_instance_with_parameter_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    database = conn.create_db_instance(
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


@mock_rds
def test_create_database_with_default_port():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        DBSecurityGroups=["my_sg"],
    )
    assert database["DBInstance"]["Endpoint"]["Port"] == 5432


@mock_rds
def test_modify_db_instance_with_parameter_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    database = conn.create_db_instance(
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

    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        DBParameterGroupName="test",
        ApplyImmediately=True,
    )

    database = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")[
        "DBInstances"
    ][0]
    assert len(database["DBParameterGroups"]) == 1
    assert database["DBParameterGroups"][0]["DBParameterGroupName"] == "test"
    assert database["DBParameterGroups"][0]["ParameterApplyStatus"] == "in-sync"


@mock_rds
def test_create_db_parameter_group_empty_description():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.create_db_parameter_group(
            DBParameterGroupName="test",
            DBParameterGroupFamily="mysql5.6",
            Description="",
        )


@mock_rds
def test_create_db_parameter_group_duplicate():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    with pytest.raises(ClientError):
        conn.create_db_parameter_group(
            DBParameterGroupName="test",
            DBParameterGroupFamily="mysql5.6",
            Description="test parameter group",
        )


@mock_rds
def test_describe_db_parameter_group():
    region = DEFAULT_REGION
    pg_name = "test"
    conn = boto3.client("rds", region_name=region)
    conn.create_db_parameter_group(
        DBParameterGroupName=pg_name,
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    assert db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "test"
    )
    assert db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupArn"] == (
        f"arn:aws:rds:{region}:{ACCOUNT_ID}:pg:{pg_name}"
    )


@mock_rds
def test_describe_non_existent_db_parameter_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    assert len(db_parameter_groups["DBParameterGroups"]) == 0


@mock_rds
def test_delete_db_parameter_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    assert db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"] == (
        "test"
    )
    conn.delete_db_parameter_group(DBParameterGroupName="test")
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    assert len(db_parameter_groups["DBParameterGroups"]) == 0


@mock_rds
def test_modify_db_parameter_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    modify_result = conn.modify_db_parameter_group(
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

    db_parameters = conn.describe_db_parameters(DBParameterGroupName="test")
    assert db_parameters["Parameters"][0]["ParameterName"] == "foo"
    assert db_parameters["Parameters"][0]["ParameterValue"] == "foo_val"
    assert db_parameters["Parameters"][0]["Description"] == "test param"
    assert db_parameters["Parameters"][0]["ApplyMethod"] == "immediate"


@mock_rds
def test_delete_non_existent_db_parameter_group():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError):
        conn.delete_db_parameter_group(DBParameterGroupName="non-existent")


@mock_rds
def test_create_parameter_group_with_tags():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
        Tags=[{"Key": "foo", "Value": "bar"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:pg:test"
    )
    assert result["TagList"] == [{"Value": "bar", "Key": "foo"}]


@mock_rds
def test_create_db_with_iam_authentication():
    conn = boto3.client("rds", region_name=DEFAULT_REGION)

    database = conn.create_db_instance(
        DBInstanceIdentifier="rds",
        DBInstanceClass="db.t1.micro",
        Engine="postgres",
        EnableIAMDatabaseAuthentication=True,
    )

    db_instance = database["DBInstance"]
    assert db_instance["IAMDatabaseAuthenticationEnabled"] is True

    snapshot = conn.create_db_snapshot(
        DBInstanceIdentifier="rds", DBSnapshotIdentifier="snapshot"
    ).get("DBSnapshot")

    assert snapshot.get("IAMDatabaseAuthenticationEnabled") is True


@mock_rds
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


@mock_rds
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


@mock_rds
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


@mock_rds
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


def validation_helper(exc):
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == (
        "The parameter DBInstanceIdentifier is not a valid identifier. "
        "Identifiers must begin with a letter; must contain only ASCII "
        "letters, digits, and hyphens; "
        "and must not end with a hyphen or contain two consecutive hyphens."
    )
