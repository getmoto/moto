import time
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_timestreamwrite, settings
from moto.core import ACCOUNT_ID


@mock_timestreamwrite
def test_create_table():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    resp = ts.create_table(
        DatabaseName="mydatabase",
        TableName="mytable",
        RetentionProperties={
            "MemoryStoreRetentionPeriodInHours": 7,
            "MagneticStoreRetentionPeriodInDays": 42,
        },
    )
    table = resp["Table"]
    table.should.have.key("Arn").equal(
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase/table/mytable"
    )
    table.should.have.key("TableName").equal("mytable")
    table.should.have.key("DatabaseName").equal("mydatabase")
    table.should.have.key("TableStatus").equal("ACTIVE")
    table.should.have.key("RetentionProperties").should.equal(
        {
            "MemoryStoreRetentionPeriodInHours": 7,
            "MagneticStoreRetentionPeriodInDays": 42,
        }
    )


@mock_timestreamwrite
def test_create_table_without_retention_properties():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    resp = ts.create_table(DatabaseName="mydatabase", TableName="mytable")
    table = resp["Table"]
    table.should.have.key("Arn").equal(
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase/table/mytable"
    )
    table.should.have.key("TableName").equal("mytable")
    table.should.have.key("DatabaseName").equal("mydatabase")
    table.should.have.key("TableStatus").equal("ACTIVE")
    table.should.have.key("RetentionProperties").equals(
        {
            "MemoryStoreRetentionPeriodInHours": 123,
            "MagneticStoreRetentionPeriodInDays": 123,
        }
    )


@mock_timestreamwrite
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
    table.should.have.key("Arn").equal(
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase/table/mytable"
    )
    table.should.have.key("TableName").equal("mytable")
    table.should.have.key("DatabaseName").equal("mydatabase")
    table.should.have.key("TableStatus").equal("ACTIVE")
    table.should.have.key("RetentionProperties").should.equal(
        {
            "MemoryStoreRetentionPeriodInHours": 10,
            "MagneticStoreRetentionPeriodInDays": 12,
        }
    )


@mock_timestreamwrite
def test_describe_unknown_database():
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")

    with pytest.raises(ClientError) as exc:
        ts.describe_table(DatabaseName="mydatabase", TableName="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The table unknown does not exist.")


@mock_timestreamwrite
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

    database.should.have.key("TableCount").equals(5)

    tables = ts.list_tables(DatabaseName="mydatabase")["Tables"]
    tables.should.have.length_of(5)
    set([t["DatabaseName"] for t in tables]).should.equal({"mydatabase"})
    set([t["TableName"] for t in tables]).should.equal(
        {"mytable_0", "mytable_1", "mytable_2", "mytable_3", "mytable_4"}
    )
    set([t["TableStatus"] for t in tables]).should.equal({"ACTIVE"})


@mock_timestreamwrite
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
    tables.should.have.length_of(3)

    ts.delete_table(DatabaseName="mydatabase", TableName="mytable_1")

    tables = ts.list_tables(DatabaseName="mydatabase")["Tables"]
    tables.should.have.length_of(2)
    set([t["TableName"] for t in tables]).should.equal({"mytable_0", "mytable_2"})


@mock_timestreamwrite
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
    table.should.have.key("RetentionProperties").equals(
        {
            "MagneticStoreRetentionPeriodInDays": 2,
            "MemoryStoreRetentionPeriodInHours": 1,
        }
    )

    table = ts.describe_table(DatabaseName="mydatabase", TableName="mytable")["Table"]
    table.should.have.key("Arn").equal(
        f"arn:aws:timestream:us-east-1:{ACCOUNT_ID}:database/mydatabase/table/mytable"
    )
    table.should.have.key("TableName").equal("mytable")
    table.should.have.key("DatabaseName").equal("mydatabase")
    table.should.have.key("TableStatus").equal("ACTIVE")
    table.should.have.key("RetentionProperties").equals(
        {
            "MagneticStoreRetentionPeriodInDays": 2,
            "MemoryStoreRetentionPeriodInHours": 1,
        }
    )


@mock_timestreamwrite
def test_write_records():
    # The query-feature is not available at the moment,
    # so there's no way for us to verify writing records is successful
    # For now, we'll just send them off into the ether and pray
    ts = boto3.client("timestream-write", region_name="us-east-1")
    ts.create_database(DatabaseName="mydatabase")
    ts.create_table(DatabaseName="mydatabase", TableName="mytable")

    # Sample records from https://docs.aws.amazon.com/timestream/latest/developerguide/code-samples.write.html
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
    resp["Total"].should.equal(len(sample_records))
    (resp["MemoryStore"] + resp["MagneticStore"]).should.equal(resp["Total"])

    if not settings.TEST_SERVER_MODE:
        from moto.timestreamwrite.models import timestreamwrite_backends

        backend = timestreamwrite_backends["us-east-1"]
        records = backend.databases["mydatabase"].tables["mytable"].records
        records.should.equal(sample_records)

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
        records.should.equal(sample_records)
