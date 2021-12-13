from __future__ import unicode_literals

import datetime
import time
import uuid

import boto3
import pytz
from botocore.exceptions import ClientError
from sure import this

from . import mock_rds


def create_db_instance(client, **kwargs):
    if "DBInstanceIdentifier" not in kwargs:
        kwargs["DBInstanceIdentifier"] = str(uuid.uuid4())
    if "DBInstanceClass" not in kwargs:
        kwargs["DBInstanceClass"] = "db.m1.small"
    if "MasterUsername" not in kwargs:
        kwargs["MasterUsername"] = "root"
    if "MasterUserPassword" not in kwargs:
        kwargs["MasterUserPassword"] = "password"
    if "Engine" not in kwargs:
        kwargs["Engine"] = "postgres"
    instance = client.create_db_instance(**kwargs)["DBInstance"]
    return instance["DBInstanceIdentifier"], instance


@mock_rds
def test_specifying_availability_zone_with_multi_az_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_instance.when.called_with(
        DBInstanceIdentifier="test-instance",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="test-db",
        DBInstanceClass="db.m4.large",
        MasterUsername="root",
        MasterUserPassword="password",
        MultiAZ=True,
        AvailabilityZone="us-west-2a",
    ).should.throw(
        ClientError,
        "Requesting a specific availability zone is not valid for Multi-AZ instances.",
    )


@mock_rds
def test_create_duplicate_db_instance_fails():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_instance(
        DBInstanceIdentifier="test-instance",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="test-db",
        DBInstanceClass="db.m4.large",
        MasterUsername="root",
        MasterUserPassword="password",
    )
    client.create_db_instance.when.called_with(
        DBInstanceIdentifier="test-instance",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="test-db",
        DBInstanceClass="db.m4.large",
        MasterUsername="root",
        MasterUserPassword="password",
    ).should.throw(ClientError, "DB Instance already exists")


@mock_rds
def test_db_instance_events():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_instance(
        DBInstanceIdentifier="test-instance",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="test-db",
        DBInstanceClass="db.m4.large",
        MasterUsername="root",
        MasterUserPassword="password",
    )
    events = client.describe_events(
        SourceIdentifier="test-instance", SourceType="db-instance"
    ).get("Events")
    this(len(events)).should.be.greater_than(0)


@mock_rds
def test_create_db_instance_with_required_parameters_only():
    client = boto3.client("rds", region_name="us-west-2")
    instance = client.create_db_instance(
        DBInstanceIdentifier="db-master-1",
        DBInstanceClass="db.m1.small",
        Engine="postgres",
    )["DBInstance"]
    instance["AllocatedStorage"].should.equal(10)
    instance.should_not.have.key("MaxAllocatedStorage")


@mock_rds
def test_max_allocated_storage():
    client = boto3.client("rds", region_name="us-west-2")
    # MaxAllocatedStorage is not set or included in details by default.
    _, details = create_db_instance(client)
    details.should_not.have.key("MaxAllocatedStorage")
    # Set at creation time.
    identifier, details = create_db_instance(client, MaxAllocatedStorage=25)
    details["MaxAllocatedStorage"].should.equal(25)
    # Set to higher limit.
    details = client.modify_db_instance(
        DBInstanceIdentifier=identifier, MaxAllocatedStorage=50
    )["DBInstance"]
    details["MaxAllocatedStorage"].should.equal(50)
    # Disable by setting equal to AllocatedStorage.
    details = client.modify_db_instance(
        DBInstanceIdentifier=identifier, MaxAllocatedStorage=details["AllocatedStorage"]
    )["DBInstance"]
    details.should_not.have.key("MaxAllocatedStorage")
    # Can't set to less than AllocatedStorage.
    client.modify_db_instance.when.called_with(
        DBInstanceIdentifier=identifier, MaxAllocatedStorage=0
    ).should.throw(ClientError, "Max storage size must be greater than storage size")


@mock_rds
def test_restore_db_instance_to_point_in_time():
    client = boto3.client("rds", region_name="us-west-2")
    source_identifier, details_source = create_db_instance(
        client, CopyTagsToSnapshot=True
    )
    details_target = client.restore_db_instance_to_point_in_time(
        SourceDBInstanceIdentifier=source_identifier,
        TargetDBInstanceIdentifier="pit-id",
        RestoreTime=datetime.datetime.fromtimestamp(
            time.time() - 600, pytz.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )["DBInstance"]
    details_target["CopyTagsToSnapshot"].should.equal(
        details_source["CopyTagsToSnapshot"]
    )
    details_target["DBInstanceClass"].should.equal(details_source["DBInstanceClass"])


# @mock_rds
# def test_invalid_parameter():
#     client = boto3.client('rds', region_name='us-west-2')
#     client.describe_db_instances(DBInstanceIdentifier='fake')
#     client.describe_db_instances(MaxRecords=500)
