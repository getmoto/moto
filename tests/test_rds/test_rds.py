from botocore.exceptions import ClientError
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from moto import mock_ec2, mock_kms, mock_rds
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_rds
def test_create_database():
    conn = boto3.client("rds", region_name="us-west-2")
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
    db_instance["AllocatedStorage"].should.equal(10)
    db_instance["DBInstanceClass"].should.equal("db.m1.small")
    db_instance["LicenseModel"].should.equal("license-included")
    db_instance["MasterUsername"].should.equal("root")
    db_instance["DBSecurityGroups"][0]["DBSecurityGroupName"].should.equal("my_sg")
    db_instance["DBInstanceArn"].should.equal(
        f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:db:db-master-1"
    )
    db_instance["DBInstanceStatus"].should.equal("available")
    db_instance["DBName"].should.equal("staging-postgres")
    db_instance["DBInstanceIdentifier"].should.equal("db-master-1")
    db_instance["IAMDatabaseAuthenticationEnabled"].should.equal(False)
    db_instance["DbiResourceId"].should.contain("db-")
    db_instance["CopyTagsToSnapshot"].should.equal(False)
    db_instance["InstanceCreateTime"].should.be.a("datetime.datetime")
    db_instance["VpcSecurityGroups"][0]["VpcSecurityGroupId"].should.equal("sg-123456")
    db_instance["DeletionProtection"].should.equal(False)
    db_instance["EnabledCloudwatchLogsExports"].should.equal(["audit", "error"])
    db_instance["Endpoint"]["Port"].should.equal(1234)
    db_instance["DbInstancePort"].should.equal(1234)


@mock_rds
def test_database_with_deletion_protection_cannot_be_deleted():
    conn = boto3.client("rds", region_name="us-west-2")
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        DeletionProtection=True,
    )
    db_instance = database["DBInstance"]
    db_instance["DBInstanceClass"].should.equal("db.m1.small")
    db_instance["DeletionProtection"].should.equal(True)


@mock_rds
def test_create_database_no_allocated_storage():
    conn = boto3.client("rds", region_name="us-west-2")
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
    )
    db_instance = database["DBInstance"]
    db_instance["Engine"].should.equal("postgres")
    db_instance["StorageType"].should.equal("gp2")
    db_instance["AllocatedStorage"].should.equal(20)
    db_instance["PreferredMaintenanceWindow"].should.equal("wed:06:38-wed:07:08")


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_more_24_hours():
    conn = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16:00-tue:17:00",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Maintenance window must be less than 24 hours.")


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_less_30_mins():
    conn = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16:00-mon:16:05",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("The maintenance window must be at least 30 minutes.")


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_value():
    conn = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="sim:16:00-mon:16:30",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain("Invalid day:hour:minute")


@mock_rds
def test_create_database_invalid_preferred_maintenance_window_format():
    conn = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.create_db_instance(
            DBInstanceIdentifier="db-master-1",
            Engine="postgres",
            DBName="staging-postgres",
            DBInstanceClass="db.m1.small",
            PreferredMaintenanceWindow="mon:16tue:17:00",
        )
    err = ex.value.response["Error"]
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain(
        "Should be specified as a range ddd:hh24:mi-ddd:hh24:mi (24H Clock UTC). Example: Sun:23:45-Mon:00:15"
    )


@mock_rds
def test_create_database_preferred_backup_window_overlap_no_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_create_database_preferred_backup_window_overlap_maintenance_window_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_create_database_preferred_backup_window_overlap_backup_window_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_create_database_preferred_backup_window_overlap_both_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_create_database_valid_preferred_maintenance_window_format():
    conn = boto3.client("rds", region_name="us-west-2")
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        PreferredMaintenanceWindow="sun:16:00-sun:16:30",
    )
    db_instance = database["DBInstance"]
    db_instance["DBInstanceClass"].should.equal("db.m1.small")
    db_instance["PreferredMaintenanceWindow"].should.equal("sun:16:00-sun:16:30")


@mock_rds
def test_create_database_valid_preferred_maintenance_window_uppercase_format():
    conn = boto3.client("rds", region_name="us-west-2")
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        PreferredMaintenanceWindow="MON:16:00-TUE:01:30",
    )
    db_instance = database["DBInstance"]
    db_instance["DBInstanceClass"].should.equal("db.m1.small")
    db_instance["PreferredMaintenanceWindow"].should.equal("mon:16:00-tue:01:30")


@mock_rds
def test_create_database_non_existing_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_instance.when.called_with(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        OptionGroupName="non-existing",
    ).should.throw(ClientError)


@mock_rds
def test_create_database_with_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
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
    db_instance["AllocatedStorage"].should.equal(10)
    db_instance["DBInstanceClass"].should.equal("db.m1.small")
    db_instance["DBName"].should.equal("staging-postgres")
    db_instance["OptionGroupMemberships"][0]["OptionGroupName"].should.equal("my-og")


@mock_rds
def test_stop_database():
    conn = boto3.client("rds", region_name="us-west-2")
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
    mydb["DBInstanceStatus"].should.equal("available")
    # test stopping database should shutdown
    response = conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["DBInstance"]["DBInstanceStatus"].should.equal("stopped")
    # test rdsclient error when trying to stop an already stopped database
    conn.stop_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    ).should.throw(ClientError)
    # test stopping a stopped database with snapshot should error and no snapshot should exist for that call
    conn.stop_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
        DBSnapshotIdentifier="rocky4570-rds-snap",
    ).should.throw(ClientError)
    response = conn.describe_db_snapshots()
    response["DBSnapshots"].should.equal([])


@mock_rds
def test_start_database():
    conn = boto3.client("rds", region_name="us-west-2")
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
    mydb["DBInstanceStatus"].should.equal("available")
    # test starting an already started database should error
    conn.start_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    ).should.throw(ClientError)
    # stop and test start - should go from stopped to available, create snapshot and check snapshot
    response = conn.stop_db_instance(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
        DBSnapshotIdentifier="rocky4570-rds-snap",
    )
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["DBInstance"]["DBInstanceStatus"].should.equal("stopped")
    response = conn.describe_db_snapshots()
    response["DBSnapshots"][0]["DBSnapshotIdentifier"].should.equal(
        "rocky4570-rds-snap"
    )
    response = conn.start_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["DBInstance"]["DBInstanceStatus"].should.equal("available")
    # starting database should not remove snapshot
    response = conn.describe_db_snapshots()
    response["DBSnapshots"][0]["DBSnapshotIdentifier"].should.equal(
        "rocky4570-rds-snap"
    )
    # test stopping database, create snapshot with existing snapshot already created should throw error
    conn.stop_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"],
        DBSnapshotIdentifier="rocky4570-rds-snap",
    ).should.throw(ClientError)
    # test stopping database not invoking snapshot should succeed.
    response = conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["DBInstance"]["DBInstanceStatus"].should.equal("stopped")


@mock_rds
def test_fail_to_stop_multi_az_and_sqlserver():
    conn = boto3.client("rds", region_name="us-west-2")
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
    mydb["DBInstanceStatus"].should.equal("available")
    # multi-az databases arent allowed to be shutdown at this time.
    conn.stop_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    ).should.throw(ClientError)
    # multi-az databases arent allowed to be started up at this time.
    conn.start_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    ).should.throw(ClientError)


@mock_rds
def test_stop_multi_az_postgres():
    conn = boto3.client("rds", region_name="us-west-2")
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
    mydb["DBInstanceStatus"].should.equal("available")

    response = conn.stop_db_instance(DBInstanceIdentifier=mydb["DBInstanceIdentifier"])
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["DBInstance"]["DBInstanceStatus"].should.equal("stopped")


@mock_rds
def test_fail_to_stop_readreplica():
    conn = boto3.client("rds", region_name="us-west-2")
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
    mydb["DBInstanceStatus"].should.equal("available")
    # read-replicas are not allowed to be stopped at this time.
    conn.stop_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    ).should.throw(ClientError)
    # read-replicas are not allowed to be started at this time.
    conn.start_db_instance.when.called_with(
        DBInstanceIdentifier=mydb["DBInstanceIdentifier"]
    ).should.throw(ClientError)


@mock_rds
def test_get_databases():
    conn = boto3.client("rds", region_name="us-west-2")

    instances = conn.describe_db_instances()
    list(instances["DBInstances"]).should.have.length_of(0)

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
    list(instances["DBInstances"]).should.have.length_of(2)

    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    list(instances["DBInstances"]).should.have.length_of(1)
    instances["DBInstances"][0]["DBInstanceIdentifier"].should.equal("db-master-1")
    instances["DBInstances"][0]["DeletionProtection"].should.equal(False)
    instances["DBInstances"][0]["DBInstanceArn"].should.equal(
        f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:db:db-master-1"
    )

    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-2")
    instances["DBInstances"][0]["DeletionProtection"].should.equal(True)
    instances["DBInstances"][0]["Endpoint"]["Port"].should.equal(1234)
    instances["DBInstances"][0]["DbInstancePort"].should.equal(1234)


@mock_rds
def test_get_databases_paginated():
    conn = boto3.client("rds", region_name="us-west-2")

    for i in range(51):
        conn.create_db_instance(
            AllocatedStorage=5,
            Port=5432,
            DBInstanceIdentifier=f"rds{i}",
            DBInstanceClass="db.t1.micro",
            Engine="postgres",
        )

    resp = conn.describe_db_instances()
    resp["DBInstances"].should.have.length_of(50)
    resp["Marker"].should.equal(resp["DBInstances"][-1]["DBInstanceIdentifier"])

    resp2 = conn.describe_db_instances(Marker=resp["Marker"])
    resp2["DBInstances"].should.have.length_of(1)

    resp3 = conn.describe_db_instances(MaxRecords=100)
    resp3["DBInstances"].should.have.length_of(51)


@mock_rds
def test_describe_non_existent_database():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.describe_db_instances.when.called_with(
        DBInstanceIdentifier="not-a-db"
    ).should.throw(ClientError)


@mock_rds
def test_modify_db_instance():
    conn = boto3.client("rds", region_name="us-west-2")
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
    instances["DBInstances"][0]["AllocatedStorage"].should.equal(10)
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=20,
        ApplyImmediately=True,
        VpcSecurityGroupIds=["sg-123456"],
    )
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    instances["DBInstances"][0]["AllocatedStorage"].should.equal(20)
    instances["DBInstances"][0]["PreferredMaintenanceWindow"].should.equal(
        "wed:06:38-wed:07:08"
    )
    instances["DBInstances"][0]["VpcSecurityGroups"][0][
        "VpcSecurityGroupId"
    ].should.equal("sg-123456")


@mock_rds
def test_modify_db_instance_not_existent_db_parameter_group_name():
    conn = boto3.client("rds", region_name="us-west-2")
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
    instances["DBInstances"][0]["AllocatedStorage"].should.equal(10)
    conn.modify_db_instance.when.called_with(
        DBInstanceIdentifier="db-master-1",
        DBParameterGroupName="test-sqlserver-se-2017",
    ).should.throw(ClientError)


@mock_rds
def test_modify_db_instance_valid_preferred_maintenance_window():
    conn = boto3.client("rds", region_name="us-west-2")
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
    instances["DBInstances"][0]["PreferredMaintenanceWindow"].should.equal(
        "sun:16:00-sun:16:30"
    )


@mock_rds
def test_modify_db_instance_valid_preferred_maintenance_window_uppercase():
    conn = boto3.client("rds", region_name="us-west-2")
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
    instances["DBInstances"][0]["PreferredMaintenanceWindow"].should.equal(
        "sun:16:00-sun:16:30"
    )


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_more_than_24_hours():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("Maintenance window must be less than 24 hours.")


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_less_than_30_mins():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal("The maintenance window must be at least 30 minutes.")


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_value():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain("Invalid day:hour:minute value")


@mock_rds
def test_modify_db_instance_invalid_preferred_maintenance_window_format():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.contain(
        "Should be specified as a range ddd:hh24:mi-ddd:hh24:mi (24H Clock UTC). Example: Sun:23:45-Mon:00:15"
    )


@mock_rds
def test_modify_db_instance_maintenance_backup_window_no_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_modify_db_instance_maintenance_backup_window_maintenance_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_modify_db_instance_maintenance_backup_window_backup_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_modify_db_instance_maintenance_backup_window_both_spill():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Code"].should.equal("InvalidParameterValue")
    err["Message"].should.equal(
        "The backup window and maintenance window must not overlap."
    )


@mock_rds
def test_rename_db_instance():
    conn = boto3.client("rds", region_name="us-west-2")
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
    list(instances["DBInstances"]).should.have.length_of(1)
    conn.describe_db_instances.when.called_with(
        DBInstanceIdentifier="db-master-2"
    ).should.throw(ClientError)
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1",
        NewDBInstanceIdentifier="db-master-2",
        ApplyImmediately=True,
    )
    conn.describe_db_instances.when.called_with(
        DBInstanceIdentifier="db-master-1"
    ).should.throw(ClientError)
    instances = conn.describe_db_instances(DBInstanceIdentifier="db-master-2")
    list(instances["DBInstances"]).should.have.length_of(1)


@mock_rds
def test_modify_non_existent_database():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.modify_db_instance.when.called_with(
        DBInstanceIdentifier="not-a-db", AllocatedStorage=20, ApplyImmediately=True
    ).should.throw(ClientError)


@mock_rds
def test_reboot_db_instance():
    conn = boto3.client("rds", region_name="us-west-2")
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
    database["DBInstance"]["DBInstanceIdentifier"].should.equal("db-master-1")


@mock_rds
def test_reboot_non_existent_database():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.reboot_db_instance.when.called_with(
        DBInstanceIdentifier="not-a-db"
    ).should.throw(ClientError)


@mock_rds
def test_delete_database():
    conn = boto3.client("rds", region_name="us-west-2")
    instances = conn.describe_db_instances()
    list(instances["DBInstances"]).should.have.length_of(0)
    conn.create_db_instance(
        DBInstanceIdentifier="db-primary-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    instances = conn.describe_db_instances()
    list(instances["DBInstances"]).should.have.length_of(1)

    conn.delete_db_instance(
        DBInstanceIdentifier="db-primary-1",
        FinalDBSnapshotIdentifier="primary-1-snapshot",
    )

    instances = conn.describe_db_instances()
    list(instances["DBInstances"]).should.have.length_of(0)

    # Saved the snapshot
    snapshots = conn.describe_db_snapshots(DBInstanceIdentifier="db-primary-1").get(
        "DBSnapshots"
    )
    snapshots[0].get("Engine").should.equal("postgres")


@mock_rds
def test_create_db_snapshots():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_snapshot.when.called_with(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).should.throw(ClientError)

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

    snapshot.get("Engine").should.equal("postgres")
    snapshot.get("DBInstanceIdentifier").should.equal("db-primary-1")
    snapshot.get("DBSnapshotIdentifier").should.equal("g-1")
    result = conn.list_tags_for_resource(ResourceName=snapshot["DBSnapshotArn"])
    result["TagList"].should.equal([])


@mock_rds
def test_create_db_snapshots_copy_tags():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_snapshot.when.called_with(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    ).should.throw(ClientError)

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

    snapshot.get("Engine").should.equal("postgres")
    snapshot.get("DBInstanceIdentifier").should.equal("db-primary-1")
    snapshot.get("DBSnapshotIdentifier").should.equal("g-1")
    result = conn.list_tags_for_resource(ResourceName=snapshot["DBSnapshotArn"])
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_copy_db_snapshots():
    conn = boto3.client("rds", region_name="us-west-2")

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

    target_snapshot.get("Engine").should.equal("postgres")
    target_snapshot.get("DBInstanceIdentifier").should.equal("db-primary-1")
    target_snapshot.get("DBSnapshotIdentifier").should.equal("snapshot-2")
    result = conn.list_tags_for_resource(ResourceName=target_snapshot["DBSnapshotArn"])
    result["TagList"].should.equal([])


@mock_rds
def test_describe_db_snapshots():
    conn = boto3.client("rds", region_name="us-west-2")
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

    created.get("Engine").should.equal("postgres")

    by_database_id = conn.describe_db_snapshots(
        DBInstanceIdentifier="db-primary-1"
    ).get("DBSnapshots")
    by_snapshot_id = conn.describe_db_snapshots(DBSnapshotIdentifier="snapshot-1").get(
        "DBSnapshots"
    )
    by_snapshot_id.should.equal(by_database_id)

    snapshot = by_snapshot_id[0]
    snapshot.should.equal(created)
    snapshot.get("Engine").should.equal("postgres")

    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-2"
    )
    snapshots = conn.describe_db_snapshots(DBInstanceIdentifier="db-primary-1").get(
        "DBSnapshots"
    )
    snapshots.should.have.length_of(2)


@mock_rds
def test_promote_read_replica():
    conn = boto3.client("rds", region_name="us-west-2")
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
    conn = boto3.client("rds", region_name="us-west-2")
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

    conn.describe_db_snapshots(DBSnapshotIdentifier="snapshot-1").get("DBSnapshots")[0]
    conn.delete_db_snapshot(DBSnapshotIdentifier="snapshot-1")
    conn.describe_db_snapshots.when.called_with(
        DBSnapshotIdentifier="snapshot-1"
    ).should.throw(ClientError)


@mock_rds
def test_restore_db_instance_from_db_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
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
    conn.describe_db_instances()["DBInstances"].should.have.length_of(1)

    conn.create_db_snapshot(
        DBInstanceIdentifier="db-primary-1", DBSnapshotIdentifier="snapshot-1"
    )

    # restore
    new_instance = conn.restore_db_instance_from_db_snapshot(
        DBInstanceIdentifier="db-restore-1", DBSnapshotIdentifier="snapshot-1"
    )["DBInstance"]
    new_instance["DBInstanceIdentifier"].should.equal("db-restore-1")
    new_instance["DBInstanceClass"].should.equal("db.m1.small")
    new_instance["StorageType"].should.equal("gp2")
    new_instance["Engine"].should.equal("postgres")
    new_instance["DBName"].should.equal("staging-postgres")
    new_instance["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "default.postgres9.3"
    )
    new_instance["DBSecurityGroups"].should.equal(
        [{"DBSecurityGroupName": "my_sg", "Status": "active"}]
    )
    new_instance["Endpoint"]["Port"].should.equal(5432)

    # Verify it exists
    conn.describe_db_instances()["DBInstances"].should.have.length_of(2)
    conn.describe_db_instances(DBInstanceIdentifier="db-restore-1")[
        "DBInstances"
    ].should.have.length_of(1)


@mock_rds
def test_restore_db_instance_from_db_snapshot_and_override_params():
    conn = boto3.client("rds", region_name="us-west-2")
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
    conn.describe_db_instances()["DBInstances"].should.have.length_of(1)
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
    new_instance["DBInstanceIdentifier"].should.equal("db-restore-1")
    new_instance["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "default.postgres9.3"
    )
    new_instance["DBSecurityGroups"].should.equal(
        [{"DBSecurityGroupName": "my_sg", "Status": "active"}]
    )
    new_instance["VpcSecurityGroups"].should.equal(
        [{"VpcSecurityGroupId": "new_vpc", "Status": "active"}]
    )
    new_instance["Endpoint"]["Port"].should.equal(10000)


@mock_rds
def test_create_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    option_group = conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_group["OptionGroup"]["OptionGroupName"].should.equal("test")
    option_group["OptionGroup"]["EngineName"].should.equal("mysql")
    option_group["OptionGroup"]["OptionGroupDescription"].should.equal(
        "test option group"
    )
    option_group["OptionGroup"]["MajorEngineVersion"].should.equal("5.6")
    option_group["OptionGroup"]["OptionGroupArn"].should.equal(
        f"arn:aws:rds:us-west-2:{ACCOUNT_ID}:og:test"
    )


@mock_rds
def test_create_option_group_bad_engine_name():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="invalid_engine",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test invalid engine",
    ).should.throw(ClientError)


@mock_rds
def test_create_option_group_bad_engine_major_version():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="6.6.6",
        OptionGroupDescription="test invalid engine version",
    ).should.throw(ClientError)


@mock_rds
def test_create_option_group_empty_description():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="",
    ).should.throw(ClientError)


@mock_rds
def test_create_option_group_duplicate():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    conn.create_option_group.when.called_with(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    ).should.throw(ClientError)


@mock_rds
def test_describe_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = conn.describe_option_groups(OptionGroupName="test")
    option_groups["OptionGroupsList"][0]["OptionGroupName"].should.equal("test")


@mock_rds
def test_describe_non_existent_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.describe_option_groups.when.called_with(
        OptionGroupName="not-a-option-group"
    ).should.throw(ClientError)


@mock_rds
def test_delete_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    option_groups = conn.describe_option_groups(OptionGroupName="test")
    option_groups["OptionGroupsList"][0]["OptionGroupName"].should.equal("test")
    conn.delete_option_group(OptionGroupName="test")
    conn.describe_option_groups.when.called_with(OptionGroupName="test").should.throw(
        ClientError
    )


@mock_rds
def test_delete_non_existent_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.delete_option_group.when.called_with(
        OptionGroupName="non-existent"
    ).should.throw(ClientError)


@mock_rds
def test_describe_option_group_options():
    conn = boto3.client("rds", region_name="us-west-2")
    option_group_options = conn.describe_option_group_options(EngineName="sqlserver-ee")
    len(option_group_options["OptionGroupOptions"]).should.equal(4)
    option_group_options = conn.describe_option_group_options(
        EngineName="sqlserver-ee", MajorEngineVersion="11.00"
    )
    len(option_group_options["OptionGroupOptions"]).should.equal(2)
    option_group_options = conn.describe_option_group_options(
        EngineName="mysql", MajorEngineVersion="5.6"
    )
    len(option_group_options["OptionGroupOptions"]).should.equal(1)
    conn.describe_option_group_options.when.called_with(
        EngineName="non-existent"
    ).should.throw(ClientError)
    conn.describe_option_group_options.when.called_with(
        EngineName="mysql", MajorEngineVersion="non-existent"
    ).should.throw(ClientError)


@mock_rds
def test_modify_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
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
    result["OptionGroup"]["EngineName"].should.equal("mysql")
    result["OptionGroup"]["Options"].should.equal([])
    result["OptionGroup"]["OptionGroupName"].should.equal("test")


@mock_rds
def test_modify_option_group_no_options():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    conn.modify_option_group.when.called_with(OptionGroupName="test").should.throw(
        ClientError
    )


@mock_rds
def test_modify_non_existent_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.modify_option_group.when.called_with(
        OptionGroupName="non-existent", OptionsToInclude=[{"OptionName": "test-option"}]
    ).should.throw(ClientError, "Specified OptionGroupName: non-existent not found.")


@mock_rds
def test_delete_database_with_protection():
    conn = boto3.client("rds", region_name="us-west-2")
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
    err["Message"].should.equal("Can't delete Instance with protection enabled")


@mock_rds
def test_delete_non_existent_database():
    conn = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        conn.delete_db_instance(DBInstanceIdentifier="non-existent")
    ex.value.response["Error"]["Code"].should.equal("DBInstanceNotFound")
    ex.value.response["Error"]["Message"].should.equal(
        "DBInstance non-existent not found."
    )


@mock_rds
def test_list_tags_invalid_arn():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.list_tags_for_resource.when.called_with(
        ResourceName="arn:aws:rds:bad-arn"
    ).should.throw(ClientError)


@mock_rds
def test_list_tags_db():
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:foo"
    )
    result["TagList"].should.equal([])
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
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_add_tags_db():
    conn = boto3.client("rds", region_name="us-west-2")
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
    list(result["TagList"]).should.have.length_of(2)
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-without-tags"
    )
    list(result["TagList"]).should.have.length_of(3)


@mock_rds
def test_remove_tags_db():
    conn = boto3.client("rds", region_name="us-west-2")
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
    list(result["TagList"]).should.have.length_of(2)
    conn.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags", TagKeys=["foo"]
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:db:db-with-tags"
    )
    len(result["TagList"]).should.equal(1)


@mock_rds
def test_list_tags_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:foo"
    )
    result["TagList"].should.equal([])
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
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_add_tags_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
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
    list(result["TagList"]).should.have.length_of(2)
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-without-tags"
    )
    list(result["TagList"]).should.have.length_of(3)


@mock_rds
def test_remove_tags_snapshot():
    conn = boto3.client("rds", region_name="us-west-2")
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
    list(result["TagList"]).should.have.length_of(2)
    conn.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags",
        TagKeys=["foo"],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:snapshot:snapshot-with-tags"
    )
    len(result["TagList"]).should.equal(1)


@mock_rds
def test_add_tags_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_option_group(
        OptionGroupName="test",
        EngineName="mysql",
        MajorEngineVersion="5.6",
        OptionGroupDescription="test option group",
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    list(result["TagList"]).should.have.length_of(0)
    conn.add_tags_to_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test",
        Tags=[{"Key": "foo", "Value": "fish"}, {"Key": "foo2", "Value": "bar2"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    list(result["TagList"]).should.have.length_of(2)


@mock_rds
def test_remove_tags_option_group():
    conn = boto3.client("rds", region_name="us-west-2")
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
    list(result["TagList"]).should.have.length_of(2)
    conn.remove_tags_from_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test", TagKeys=["foo"]
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:og:test"
    )
    list(result["TagList"]).should.have.length_of(1)


@mock_rds
def test_create_database_security_group():
    conn = boto3.client("rds", region_name="us-west-2")

    result = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    result["DBSecurityGroup"]["DBSecurityGroupName"].should.equal("db_sg")
    result["DBSecurityGroup"]["DBSecurityGroupDescription"].should.equal(
        "DB Security Group"
    )
    result["DBSecurityGroup"]["IPRanges"].should.equal([])


@mock_rds
def test_get_security_groups():
    conn = boto3.client("rds", region_name="us-west-2")

    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(0)

    conn.create_db_security_group(
        DBSecurityGroupName="db_sg1", DBSecurityGroupDescription="DB Security Group"
    )
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg2", DBSecurityGroupDescription="DB Security Group"
    )

    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(2)

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg1")
    result["DBSecurityGroups"].should.have.length_of(1)
    result["DBSecurityGroups"][0]["DBSecurityGroupName"].should.equal("db_sg1")


@mock_rds
def test_get_non_existent_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.describe_db_security_groups.when.called_with(
        DBSecurityGroupName="not-a-sg"
    ).should.throw(ClientError)


@mock_rds
def test_delete_database_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )

    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(1)

    conn.delete_db_security_group(DBSecurityGroupName="db_sg")
    result = conn.describe_db_security_groups()
    result["DBSecurityGroups"].should.have.length_of(0)


@mock_rds
def test_delete_non_existent_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.delete_db_security_group.when.called_with(
        DBSecurityGroupName="not-a-db"
    ).should.throw(ClientError)


@mock_rds
def test_security_group_authorize():
    conn = boto3.client("rds", region_name="us-west-2")
    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    security_group["DBSecurityGroup"]["IPRanges"].should.equal([])

    conn.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.45/32"
    )

    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    result["DBSecurityGroups"][0]["IPRanges"].should.have.length_of(1)
    result["DBSecurityGroups"][0]["IPRanges"].should.equal(
        [{"Status": "authorized", "CIDRIP": "10.3.2.45/32"}]
    )

    conn.authorize_db_security_group_ingress(
        DBSecurityGroupName="db_sg", CIDRIP="10.3.2.46/32"
    )
    result = conn.describe_db_security_groups(DBSecurityGroupName="db_sg")
    result["DBSecurityGroups"][0]["IPRanges"].should.have.length_of(2)
    result["DBSecurityGroups"][0]["IPRanges"].should.equal(
        [
            {"Status": "authorized", "CIDRIP": "10.3.2.45/32"},
            {"Status": "authorized", "CIDRIP": "10.3.2.46/32"},
        ]
    )


@mock_rds
def test_add_security_group_to_database():
    conn = boto3.client("rds", region_name="us-west-2")

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
    result["DBInstances"][0]["DBSecurityGroups"].should.equal([])
    conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )
    conn.modify_db_instance(
        DBInstanceIdentifier="db-master-1", DBSecurityGroups=["db_sg"]
    )
    result = conn.describe_db_instances()
    result["DBInstances"][0]["DBSecurityGroups"][0]["DBSecurityGroupName"].should.equal(
        "db_sg"
    )


@mock_rds
def test_list_tags_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSecurityGroup"]["DBSecurityGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_add_tags_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg", DBSecurityGroupDescription="DB Security Group"
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    conn.add_tags_to_resource(
        ResourceName=resource,
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )

    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_remove_tags_security_group():
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    security_group = conn.create_db_security_group(
        DBSecurityGroupName="db_sg",
        DBSecurityGroupDescription="DB Security Group",
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSecurityGroup"]["DBSecurityGroupName"]

    resource = f"arn:aws:rds:us-west-2:1234567890:secgrp:{security_group}"
    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=["foo"])

    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal([{"Value": "bar1", "Key": "foo1"}])


@mock_ec2
@mock_rds
def test_create_database_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]
    subnet2 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.2.0/24")[
        "Subnet"
    ]

    subnet_ids = [subnet1["SubnetId"], subnet2["SubnetId"]]
    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=subnet_ids,
    )
    result["DBSubnetGroup"]["DBSubnetGroupName"].should.equal("db_subnet")
    result["DBSubnetGroup"]["DBSubnetGroupDescription"].should.equal("my db subnet")
    subnets = result["DBSubnetGroup"]["Subnets"]
    subnet_group_ids = [subnets[0]["SubnetIdentifier"], subnets[1]["SubnetIdentifier"]]
    list(subnet_group_ids).should.equal(subnet_ids)


@mock_ec2
@mock_rds
def test_modify_database_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet1 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]
    subnet2 = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.2.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name="us-west-2")
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

    conn.describe_db_subnet_groups()["DBSubnetGroups"]
    # FIXME: Group is deleted atm
    # TODO: we should check whether all attrs are persisted


@mock_ec2
@mock_rds
def test_create_database_in_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name="us-west-2")
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
    result["DBInstances"][0]["DBSubnetGroup"]["DBSubnetGroupName"].should.equal(
        "db_subnet1"
    )


@mock_ec2
@mock_rds
def test_describe_database_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name="us-west-2")
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
    resp["DBSubnetGroups"].should.have.length_of(2)

    subnets = resp["DBSubnetGroups"][0]["Subnets"]
    subnets.should.have.length_of(1)

    list(
        conn.describe_db_subnet_groups(DBSubnetGroupName="db_subnet1")["DBSubnetGroups"]
    ).should.have.length_of(1)

    conn.describe_db_subnet_groups.when.called_with(
        DBSubnetGroupName="not-a-subnet"
    ).should.throw(ClientError)


@mock_ec2
@mock_rds
def test_delete_database_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
    )
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(1)

    conn.delete_db_subnet_group(DBSubnetGroupName="db_subnet1")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    conn.delete_db_subnet_group.when.called_with(
        DBSubnetGroupName="db_subnet1"
    ).should.throw(ClientError)


@mock_ec2
@mock_rds
def test_list_tags_database_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    subnet = conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    result = conn.list_tags_for_resource(
        ResourceName=f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"
    )
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_rds
def test_modify_tags_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    client_tags = [{"Key": "character_set_client", "Value": "utf-8"}]
    result = conn.create_db_parameter_group(
        DBParameterGroupName="test-sqlserver-2017",
        DBParameterGroupFamily="mysql5.6",
        Description="MySQL Group",
        Tags=client_tags,
    )
    resource = result["DBParameterGroup"]["DBParameterGroupArn"]
    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(client_tags)
    server_tags = [{"Key": "character_set_server", "Value": "utf-8"}]
    conn.add_tags_to_resource(ResourceName=resource, Tags=server_tags)
    combined_tags = client_tags + server_tags
    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(combined_tags)

    conn.remove_tags_from_resource(
        ResourceName=resource, TagKeys=["character_set_client"]
    )
    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(server_tags)


@mock_rds
def test_modify_tags_event_subscription():
    conn = boto3.client("rds", region_name="us-west-2")
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
    result["TagList"].should.equal(tags)
    new_tags = [{"Key": "new_key", "Value": "new_value"}]
    conn.add_tags_to_resource(ResourceName=resource, Tags=new_tags)
    combined_tags = tags + new_tags
    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(combined_tags)

    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=["new_key"])
    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal(tags)


@mock_ec2
@mock_rds
def test_add_tags_database_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

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
    result["TagList"].should.equal(
        [{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}]
    )


@mock_ec2
@mock_rds
def test_remove_tags_database_subnet_group():
    vpc_conn = boto3.client("ec2", "us-west-2")
    vpc = vpc_conn.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]
    subnet = vpc_conn.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.1.0/24")[
        "Subnet"
    ]

    conn = boto3.client("rds", region_name="us-west-2")
    result = conn.describe_db_subnet_groups()
    result["DBSubnetGroups"].should.have.length_of(0)

    subnet = conn.create_db_subnet_group(
        DBSubnetGroupName="db_subnet1",
        DBSubnetGroupDescription="my db subnet",
        SubnetIds=[subnet["SubnetId"]],
        Tags=[{"Value": "bar", "Key": "foo"}, {"Value": "bar1", "Key": "foo1"}],
    )["DBSubnetGroup"]["DBSubnetGroupName"]
    resource = f"arn:aws:rds:us-west-2:1234567890:subgrp:{subnet}"

    conn.remove_tags_from_resource(ResourceName=resource, TagKeys=["foo"])

    result = conn.list_tags_for_resource(ResourceName=resource)
    result["TagList"].should.equal([{"Value": "bar1", "Key": "foo1"}])


@mock_rds
def test_create_database_replica():
    conn = boto3.client("rds", region_name="us-west-2")

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
    replica["DBInstance"]["ReadReplicaSourceDBInstanceIdentifier"].should.equal(
        "db-master-1"
    )
    replica["DBInstance"]["DBInstanceClass"].should.equal("db.m1.small")
    replica["DBInstance"]["DBInstanceIdentifier"].should.equal("db-replica-1")

    master = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    master["DBInstances"][0]["ReadReplicaDBInstanceIdentifiers"].should.equal(
        ["db-replica-1"]
    )
    replica = conn.describe_db_instances(DBInstanceIdentifier="db-replica-1")[
        "DBInstances"
    ][0]
    replica["ReadReplicaSourceDBInstanceIdentifier"].should.equal("db-master-1")

    conn.delete_db_instance(DBInstanceIdentifier="db-replica-1", SkipFinalSnapshot=True)

    master = conn.describe_db_instances(DBInstanceIdentifier="db-master-1")
    master["DBInstances"][0]["ReadReplicaDBInstanceIdentifiers"].should.equal([])


@mock_rds
def test_create_database_replica_cross_region():
    us1 = boto3.client("rds", region_name="us-east-1")
    us2 = boto3.client("rds", region_name="us-west-2")

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
    source_db.should.have.key("ReadReplicaDBInstanceIdentifiers").equals([target_arn])

    target_db = us2.describe_db_instances(DBInstanceIdentifier=target_id)[
        "DBInstances"
    ][0]
    target_db.should.have.key("ReadReplicaSourceDBInstanceIdentifier").equals(
        source_arn
    )


@mock_rds
@mock_kms
def test_create_database_with_encrypted_storage():
    kms_conn = boto3.client("kms", region_name="us-west-2")
    key = kms_conn.create_key(
        Policy="my RDS encryption policy",
        Description="RDS encryption key",
        KeyUsage="ENCRYPT_DECRYPT",
    )

    conn = boto3.client("rds", region_name="us-west-2")
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

    database["DBInstance"]["StorageEncrypted"].should.equal(True)
    database["DBInstance"]["KmsKeyId"].should.equal(key["KeyMetadata"]["KeyId"])


@mock_rds
def test_create_db_parameter_group():
    region = "us-west-2"
    pg_name = "test"
    conn = boto3.client("rds", region_name=region)
    db_parameter_group = conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )

    db_parameter_group["DBParameterGroup"]["DBParameterGroupName"].should.equal("test")
    db_parameter_group["DBParameterGroup"]["DBParameterGroupFamily"].should.equal(
        "mysql5.6"
    )
    db_parameter_group["DBParameterGroup"]["Description"].should.equal(
        "test parameter group"
    )
    db_parameter_group["DBParameterGroup"]["DBParameterGroupArn"].should.equal(
        f"arn:aws:rds:{region}:{ACCOUNT_ID}:pg:{pg_name}"
    )


@mock_rds
def test_create_db_instance_with_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
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

    len(database["DBInstance"]["DBParameterGroups"]).should.equal(1)
    database["DBInstance"]["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "test"
    )
    database["DBInstance"]["DBParameterGroups"][0]["ParameterApplyStatus"].should.equal(
        "in-sync"
    )


@mock_rds
def test_create_database_with_default_port():
    conn = boto3.client("rds", region_name="us-west-2")
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        DBSecurityGroups=["my_sg"],
    )
    database["DBInstance"]["Endpoint"]["Port"].should.equal(5432)


@mock_rds
def test_modify_db_instance_with_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    database = conn.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        AllocatedStorage=10,
        Engine="mysql",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
    )

    len(database["DBInstance"]["DBParameterGroups"]).should.equal(1)
    database["DBInstance"]["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "default.mysql5.6"
    )
    database["DBInstance"]["DBParameterGroups"][0]["ParameterApplyStatus"].should.equal(
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
    len(database["DBParameterGroups"]).should.equal(1)
    database["DBParameterGroups"][0]["DBParameterGroupName"].should.equal("test")
    database["DBParameterGroups"][0]["ParameterApplyStatus"].should.equal("in-sync")


@mock_rds
def test_create_db_parameter_group_empty_description():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group.when.called_with(
        DBParameterGroupName="test", DBParameterGroupFamily="mysql5.6", Description=""
    ).should.throw(ClientError)


@mock_rds
def test_create_db_parameter_group_duplicate():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    conn.create_db_parameter_group.when.called_with(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    ).should.throw(ClientError)


@mock_rds
def test_describe_db_parameter_group():
    region = "us-west-2"
    pg_name = "test"
    conn = boto3.client("rds", region_name=region)
    conn.create_db_parameter_group(
        DBParameterGroupName=pg_name,
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "test"
    )
    db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupArn"].should.equal(
        f"arn:aws:rds:{region}:{ACCOUNT_ID}:pg:{pg_name}"
    )


@mock_rds
def test_describe_non_existent_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    len(db_parameter_groups["DBParameterGroups"]).should.equal(0)


@mock_rds
def test_delete_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
    )
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    db_parameter_groups["DBParameterGroups"][0]["DBParameterGroupName"].should.equal(
        "test"
    )
    conn.delete_db_parameter_group(DBParameterGroupName="test")
    db_parameter_groups = conn.describe_db_parameter_groups(DBParameterGroupName="test")
    len(db_parameter_groups["DBParameterGroups"]).should.equal(0)


@mock_rds
def test_modify_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
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

    modify_result["DBParameterGroupName"].should.equal("test")

    db_parameters = conn.describe_db_parameters(DBParameterGroupName="test")
    db_parameters["Parameters"][0]["ParameterName"].should.equal("foo")
    db_parameters["Parameters"][0]["ParameterValue"].should.equal("foo_val")
    db_parameters["Parameters"][0]["Description"].should.equal("test param")
    db_parameters["Parameters"][0]["ApplyMethod"].should.equal("immediate")


@mock_rds
def test_delete_non_existent_db_parameter_group():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.delete_db_parameter_group.when.called_with(
        DBParameterGroupName="non-existent"
    ).should.throw(ClientError)


@mock_rds
def test_create_parameter_group_with_tags():
    conn = boto3.client("rds", region_name="us-west-2")
    conn.create_db_parameter_group(
        DBParameterGroupName="test",
        DBParameterGroupFamily="mysql5.6",
        Description="test parameter group",
        Tags=[{"Key": "foo", "Value": "bar"}],
    )
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:rds:us-west-2:1234567890:pg:test"
    )
    result["TagList"].should.equal([{"Value": "bar", "Key": "foo"}])


@mock_rds
def test_create_db_with_iam_authentication():
    conn = boto3.client("rds", region_name="us-west-2")

    database = conn.create_db_instance(
        DBInstanceIdentifier="rds",
        DBInstanceClass="db.t1.micro",
        Engine="postgres",
        EnableIAMDatabaseAuthentication=True,
    )

    db_instance = database["DBInstance"]
    db_instance["IAMDatabaseAuthenticationEnabled"].should.equal(True)


@mock_rds
def test_create_db_snapshot_with_iam_authentication():
    conn = boto3.client("rds", region_name="us-west-2")

    conn.create_db_instance(
        DBInstanceIdentifier="rds",
        DBInstanceClass="db.t1.micro",
        Engine="postgres",
        EnableIAMDatabaseAuthentication=True,
    )

    snapshot = conn.create_db_snapshot(
        DBInstanceIdentifier="rds", DBSnapshotIdentifier="snapshot"
    ).get("DBSnapshot")

    snapshot.get("IAMDatabaseAuthenticationEnabled").should.equal(True)


@mock_rds
def test_create_db_instance_with_tags():
    client = boto3.client("rds", region_name="us-west-2")
    tags = [{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}]
    db_instance_identifier = "test-db-instance"
    resp = client.create_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        Tags=tags,
    )
    resp["DBInstance"]["TagList"].should.equal(tags)

    resp = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    resp["DBInstances"][0]["TagList"].should.equal(tags)


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
    resp["DBInstance"]["AvailabilityZone"].should.contain(region)

    resp = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    resp["DBInstances"][0]["AvailabilityZone"].should.contain(region)


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
    resp["DBInstance"]["AvailabilityZone"].should.equal(availability_zone)

    resp = client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    resp["DBInstances"][0]["AvailabilityZone"].should.equal(availability_zone)
