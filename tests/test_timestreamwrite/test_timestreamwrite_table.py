import time
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import aws_verified


@pytest.mark.aws_verified
@aws_verified
def test_create_table():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_name = "db_" + str(uuid4())[0:6]
    table_name = "t_" + str(uuid4())[0:6]

    identity = boto3.client("sts", region_name="us-east-1").get_caller_identity()
    account_id = identity["Account"]

    try:
        ts.create_database(DatabaseName=db_name)

        resp = ts.create_table(
            DatabaseName=db_name,
            TableName=table_name,
            RetentionProperties={
                "MemoryStoreRetentionPeriodInHours": 7,
                "MagneticStoreRetentionPeriodInDays": 42,
            },
        )
        table = resp["Table"]
        assert table["Arn"] == (
            f"arn:aws:timestream:us-east-1:{account_id}:database/{db_name}/table/{table_name}"
        )
        assert table["TableName"] == table_name
        assert table["DatabaseName"] == db_name
        assert table["TableStatus"] == "ACTIVE"
        assert table["RetentionProperties"] == {
            "MemoryStoreRetentionPeriodInHours": 7,
            "MagneticStoreRetentionPeriodInDays": 42,
        }
    finally:
        ts.delete_table(DatabaseName=db_name, TableName=table_name)
        ts.delete_database(DatabaseName=db_name)


@pytest.mark.aws_verified
@aws_verified
def test_create_table__with_magnetic_store_write_properties():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_name = "db_" + str(uuid4())[0:6]
    table_name = "t_" + str(uuid4())[0:6]

    identity = boto3.client("sts", region_name="us-east-1").get_caller_identity()
    account_id = identity["Account"]

    bucket_name = f"b-{str(uuid4())[0:6]}"
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=bucket_name)

    try:
        ts.create_database(DatabaseName=db_name)

        table = ts.create_table(
            DatabaseName=db_name,
            TableName=table_name,
            MagneticStoreWriteProperties={
                "EnableMagneticStoreWrites": True,
                "MagneticStoreRejectedDataLocation": {
                    "S3Configuration": {"BucketName": bucket_name}
                },
            },
        )["Table"]
        assert table["Arn"] == (
            f"arn:aws:timestream:us-east-1:{account_id}:database/{db_name}/table/{table_name}"
        )
        assert table["TableName"] == table_name
        assert table["DatabaseName"] == db_name
        assert table["TableStatus"] == "ACTIVE"
        assert table["MagneticStoreWriteProperties"] == {
            "EnableMagneticStoreWrites": True,
            "MagneticStoreRejectedDataLocation": {
                "S3Configuration": {"BucketName": bucket_name}
            },
        }
    finally:
        ts.delete_table(DatabaseName=db_name, TableName=table_name)
        ts.delete_database(DatabaseName=db_name)
        s3.delete_bucket(Bucket=bucket_name)


@pytest.mark.aws_verified
@aws_verified
def test_create_table_without_retention_properties():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_name = "db_" + str(uuid4())[0:6]
    table_name = "t_" + str(uuid4())[0:6]

    identity = boto3.client("sts", region_name="us-east-1").get_caller_identity()
    account_id = identity["Account"]

    try:
        ts.create_database(DatabaseName=db_name)

        table = ts.create_table(DatabaseName=db_name, TableName=table_name)["Table"]
        assert table["Arn"] == (
            f"arn:aws:timestream:us-east-1:{account_id}:database/{db_name}/table/{table_name}"
        )
        assert table["TableName"] == table_name
        assert table["DatabaseName"] == db_name
        assert table["TableStatus"] == "ACTIVE"
        assert table["RetentionProperties"] == {
            "MemoryStoreRetentionPeriodInHours": 6,
            "MagneticStoreRetentionPeriodInDays": 73000,
        }
    finally:
        ts.delete_table(DatabaseName=db_name, TableName=table_name)
        ts.delete_database(DatabaseName=db_name)


@mock_aws
def test_describe_table():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    ts.create_table(
        DatabaseName="mydatabase",
        TableName="mytable",
        RetentionProperties={
            "MemoryStoreRetentionPeriodInHours": 10,
            "MagneticStoreRetentionPeriodInDays": 12,
        },
    )

    table = ts.describe_table(DatabaseName="mydatabase", TableName="mytable")["Table"]
    assert table["Arn"] == (
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase/table/mytable"
    )
    assert table["TableName"] == "mytable"
    assert table["DatabaseName"] == "mydatabase"
    assert table["TableStatus"] == "ACTIVE"
    assert table["RetentionProperties"] == {
        "MemoryStoreRetentionPeriodInHours": 10,
        "MagneticStoreRetentionPeriodInDays": 12,
    }


@pytest.mark.aws_verified
@aws_verified
def test_describe_unknown_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    db_name = "db_" + str(uuid4())[0:6]

    try:
        ts.create_database(DatabaseName=db_name)

        with pytest.raises(ClientError) as exc:
            ts.describe_table(DatabaseName=db_name, TableName="unknown")
        err = exc.value.response["Error"]
        assert err["Code"] == "ResourceNotFoundException"
        assert err["Message"] == "The table unknown does not exist."
    finally:
        ts.delete_database(DatabaseName=db_name)


@mock_aws
def test_create_multiple_tables():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    for idx in range(0, 5):
        ts.create_table(
            DatabaseName="mydatabase",
            TableName=f"mytable_{idx}",
            RetentionProperties={
                "MemoryStoreRetentionPeriodInHours": 7,
                "MagneticStoreRetentionPeriodInDays": 42,
            },
        )

    database = ts.describe_database(DatabaseName="mydatabase")["Database"]

    assert database["TableCount"] == 5

    tables = ts.list_tables(DatabaseName="mydatabase")["Tables"]
    assert len(tables) == 5
    assert {t["DatabaseName"] for t in tables} == {"mydatabase"}
    assert {t["TableName"] for t in tables} == {
        "mytable_0",
        "mytable_1",
        "mytable_2",
        "mytable_3",
        "mytable_4",
    }
    assert {t["TableStatus"] for t in tables} == {"ACTIVE"}


@mock_aws
def test_delete_table():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    for idx in range(0, 3):
        ts.create_table(
            DatabaseName="mydatabase",
            TableName=f"mytable_{idx}",
            RetentionProperties={
                "MemoryStoreRetentionPeriodInHours": 7,
                "MagneticStoreRetentionPeriodInDays": 42,
            },
        )

    tables = ts.list_tables(DatabaseName="mydatabase")["Tables"]
    assert len(tables) == 3

    ts.delete_table(DatabaseName="mydatabase", TableName="mytable_1")

    tables = ts.list_tables(DatabaseName="mydatabase")["Tables"]
    assert len(tables) == 2
    assert {t["TableName"] for t in tables} == {"mytable_0", "mytable_2"}


@mock_aws
def test_update_table():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")
    ts.create_table(DatabaseName="mydatabase", TableName="mytable")

    resp = ts.update_table(
        DatabaseName="mydatabase",
        TableName="mytable",
        RetentionProperties={
            "MemoryStoreRetentionPeriodInHours": 1,
            "MagneticStoreRetentionPeriodInDays": 2,
        },
    )
    table = resp["Table"]
    assert table["RetentionProperties"] == {
        "MagneticStoreRetentionPeriodInDays": 2,
        "MemoryStoreRetentionPeriodInHours": 1,
    }

    table = ts.describe_table(DatabaseName="mydatabase", TableName="mytable")["Table"]
    assert table["Arn"] == (
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase/table/mytable"
    )
    assert table["TableName"] == "mytable"
    assert table["DatabaseName"] == "mydatabase"
    assert table["TableStatus"] == "ACTIVE"
    assert table["RetentionProperties"] == {
        "MagneticStoreRetentionPeriodInDays": 2,
        "MemoryStoreRetentionPeriodInHours": 1,
    }


@mock_aws
def test_update_table__with_magnetic_store_write_properties():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    ts.create_table(DatabaseName="mydatabase", TableName="mytable")

    resp = ts.update_table(
        DatabaseName="mydatabase",
        TableName="mytable",
        MagneticStoreWriteProperties={
            "EnableMagneticStoreWrites": True,
            "MagneticStoreRejectedDataLocation": {
                "S3Configuration": {"BucketName": "hithere"}
            },
        },
    )
    table = resp["Table"]
    assert table["Arn"] == (
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase/table/mytable"
    )
    assert table["TableName"] == "mytable"
    assert table["DatabaseName"] == "mydatabase"
    assert table["TableStatus"] == "ACTIVE"
    assert table["MagneticStoreWriteProperties"] == {
        "EnableMagneticStoreWrites": True,
        "MagneticStoreRejectedDataLocation": {
            "S3Configuration": {"BucketName": "hithere"}
        },
    }


@mock_aws
def test_write_records():
    # The query-feature is not available at the moment,
    # so there's no way for us to verify writing records is successful
    # For now, we'll just send them off into the ether and pray
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")
    ts.create_table(DatabaseName="mydatabase", TableName="mytable")

    # Sample records from:
    # https://docs.aws.amazon.com/timestream/latest/developerguide/code-samples.write.html
    dimensions = [
        {"Name": "region", "Value": "us-east-1"},
        {"Name": "az", "Value": "az1"},
        {"Name": "hostname", "Value": "host1"},
    ]

    cpu_utilization = {
        "Dimensions": dimensions,
        "MeasureName": "cpu_utilization",
        "MeasureValue": "13.5",
        "MeasureValueType": "DOUBLE",
        "Time": str(time.time()),
    }

    memory_utilization = {
        "Dimensions": dimensions,
        "MeasureName": "memory_utilization",
        "MeasureValue": "40",
        "MeasureValueType": "DOUBLE",
        "Time": str(time.time()),
    }

    sample_records = [cpu_utilization, memory_utilization]

    resp = ts.write_records(
        DatabaseName="mydatabase",
        TableName="mytable",
        Records=sample_records,
    ).get("RecordsIngested", {})
    assert resp["Total"] == len(sample_records)
    assert (resp["MemoryStore"] + resp["MagneticStore"]) == resp["Total"]

    if not settings.TEST_SERVER_MODE:
        from moto.timestreamwrite.models import timestreamwrite_backends

        backend = timestreamwrite_backends[ACCOUNT_ID]["us-east-1"]
        records = backend.databases["mydatabase"].tables["mytable"].records
        assert records == sample_records

        disk_utilization = {
            "Dimensions": dimensions,
            "MeasureName": "disk_utilization",
            "MeasureValue": "100",
            "MeasureValueType": "DOUBLE",
            "Time": str(time.time()),
        }
        sample_records.append(disk_utilization)

        ts.write_records(
            DatabaseName="mydatabase",
            TableName="mytable",
            Records=[disk_utilization],
        )
        assert records == sample_records
