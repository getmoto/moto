import boto3
import sure  # noqa # pylint: disable=unused-import
from moto import mock_timestreamwrite
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
    table.shouldnt.have.key("RetentionProperties")


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

    ts.write_records(
        DatabaseName="mydatabase",
        TableName="mytable",
        Records=[{"Dimensions": [], "MeasureName": "mn", "MeasureValue": "mv"}],
    )
