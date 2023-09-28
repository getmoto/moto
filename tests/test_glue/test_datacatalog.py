import pytest
import json
import boto3
from botocore.client import ClientError


from datetime import datetime, timezone
from freezegun import freeze_time

from moto import mock_glue, settings
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from . import helpers


FROZEN_CREATE_TIME = datetime(2015, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


@mock_glue
@freeze_time(FROZEN_CREATE_TIME)
def test_create_database():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    database_catalog_id = ACCOUNT_ID
    database_input = helpers.create_database_input(database_name)
    helpers.create_database(client, database_name, database_input, database_catalog_id)

    response = helpers.get_database(client, database_name)
    database = response["Database"]

    assert database["Name"] == database_name
    assert database["CatalogId"] == ACCOUNT_ID
    assert database.get("Description") == database_input.get("Description")
    assert database.get("LocationUri") == database_input.get("LocationUri")
    assert database.get("Parameters") == database_input.get("Parameters")
    if not settings.TEST_SERVER_MODE:
        assert database["CreateTime"].timestamp() == FROZEN_CREATE_TIME.timestamp()
    assert database["CreateTableDefaultPermissions"] == database_input.get(
        "CreateTableDefaultPermissions"
    )
    assert database.get("TargetDatabase") == database_input.get("TargetDatabase")
    assert database.get("CatalogId") == database_catalog_id


@mock_glue
def test_create_database_already_exists():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "cantcreatethisdatabasetwice"
    helpers.create_database(client, database_name)

    with pytest.raises(ClientError) as exc:
        helpers.create_database(client, database_name)

    assert exc.value.response["Error"]["Code"] == "AlreadyExistsException"


@mock_glue
def test_get_database_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "nosuchdatabase"

    with pytest.raises(ClientError) as exc:
        helpers.get_database(client, database_name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert (
        exc.value.response["Error"]["Message"] == "Database nosuchdatabase not found."
    )


@mock_glue
def test_get_databases():
    client = boto3.client("glue", region_name="us-east-1")
    response = client.get_databases()
    assert len(response["DatabaseList"]) == 0

    client = boto3.client("glue", region_name="us-east-1")
    database_name_1, database_name_2 = "firstdatabase", "seconddatabase"

    helpers.create_database(client, database_name_1, {"Name": database_name_1})
    helpers.create_database(client, database_name_2, {"Name": database_name_2})

    database_list = sorted(
        client.get_databases()["DatabaseList"], key=lambda x: x["Name"]
    )
    assert len(database_list) == 2
    assert database_list[0]["Name"] == database_name_1
    assert database_list[0]["CatalogId"] == ACCOUNT_ID
    assert database_list[1]["Name"] == database_name_2
    assert database_list[1]["CatalogId"] == ACCOUNT_ID


@mock_glue
def test_update_database():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "existingdatabase"
    database_catalog_id = ACCOUNT_ID
    helpers.create_database(
        client, database_name, {"Name": database_name}, database_catalog_id
    )

    response = helpers.get_database(client, database_name)
    database = response["Database"]
    assert database.get("CatalogId") == database_catalog_id
    assert database.get("Description") is None
    assert database.get("LocationUri") is None

    database_input = {
        "Name": database_name,
        "Description": "desc",
        "LocationUri": "s3://bucket/existingdatabase/",
    }
    client.update_database(
        CatalogId=database_catalog_id, Name=database_name, DatabaseInput=database_input
    )

    response = helpers.get_database(client, database_name)
    database = response["Database"]
    assert database.get("CatalogId") == database_catalog_id
    assert database.get("Description") == "desc"
    assert database.get("LocationUri") == "s3://bucket/existingdatabase/"


@mock_glue
def test_update_unknown_database():
    client = boto3.client("glue", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.update_database(Name="x", DatabaseInput={"Name": "x"})
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert err["Message"] == "Database x not found."


@mock_glue
def test_delete_database():
    client = boto3.client("glue", region_name="us-east-1")
    database_name_1, database_name_2 = "firstdatabase", "seconddatabase"

    helpers.create_database(client, database_name_1, {"Name": database_name_1})
    helpers.create_database(client, database_name_2, {"Name": database_name_2})

    client.delete_database(Name=database_name_1)

    database_list = sorted(
        client.get_databases()["DatabaseList"], key=lambda x: x["Name"]
    )
    assert [db["Name"] for db in database_list] == [database_name_2]


@mock_glue
def test_delete_unknown_database():
    client = boto3.client("glue", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_database(Name="x")
    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert err["Message"] == "Database x not found."


@mock_glue
@freeze_time(FROZEN_CREATE_TIME)
def test_create_table():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "myspecialtable"
    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)

    response = helpers.get_table(client, database_name, table_name)
    table = response["Table"]

    if not settings.TEST_SERVER_MODE:
        assert table["CreateTime"].timestamp() == FROZEN_CREATE_TIME.timestamp()

    assert table["Name"] == table_input["Name"]
    assert table["StorageDescriptor"] == table_input["StorageDescriptor"]
    assert table["PartitionKeys"] == table_input["PartitionKeys"]


@mock_glue
def test_create_table_already_exists():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "cantcreatethistabletwice"
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.create_table(client, database_name, table_name)

    assert exc.value.response["Error"]["Code"] == "AlreadyExistsException"


@mock_glue
def test_get_tables():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_names = ["myfirsttable", "mysecondtable", "mythirdtable"]
    table_inputs = {}

    for table_name in table_names:
        table_input = helpers.create_table_input(database_name, table_name)
        table_inputs[table_name] = table_input
        helpers.create_table(client, database_name, table_name, table_input)

    response = helpers.get_tables(client, database_name)

    tables = response["TableList"]

    assert len(tables) == 3

    for table in tables:
        table_name = table["Name"]
        assert table_name == table_inputs[table_name]["Name"]
        assert (
            table["StorageDescriptor"] == table_inputs[table_name]["StorageDescriptor"]
        )
        assert table["PartitionKeys"] == table_inputs[table_name]["PartitionKeys"]
        assert table["CatalogId"] == ACCOUNT_ID


@mock_glue
def test_get_tables_expression():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_names = [
        "mytableprefix_123",
        "mytableprefix_something_test",
        "something_mytablepostfix",
        "test_catchthis123_test",
        "asduas6781catchthisasdas",
        "fakecatchthisfake",
        "trailingtest.",
        "trailingtest...",
    ]
    table_inputs = {}

    for table_name in table_names:
        table_input = helpers.create_table_input(database_name, table_name)
        table_inputs[table_name] = table_input
        helpers.create_table(client, database_name, table_name, table_input)

    prefix_expression = "mytableprefix_\\w+"
    postfix_expression = "\\w+_mytablepostfix"
    string_expression = "\\w+catchthis\\w+"

    # even though * is an invalid regex, sadly glue api treats it as a glob-like wildcard
    star_expression1 = "*"
    star_expression2 = "mytable*"
    star_expression3 = "*table*"
    star_expression4 = "*catch*is*"
    star_expression5 = ".*catch*is*"
    star_expression6 = "trailing*.*"

    response_prefix = helpers.get_tables(client, database_name, prefix_expression)
    response_postfix = helpers.get_tables(client, database_name, postfix_expression)
    response_string_match = helpers.get_tables(client, database_name, string_expression)
    response_star_expression1 = helpers.get_tables(
        client, database_name, star_expression1
    )
    response_star_expression2 = helpers.get_tables(
        client, database_name, star_expression2
    )
    response_star_expression3 = helpers.get_tables(
        client, database_name, star_expression3
    )
    response_star_expression4 = helpers.get_tables(
        client, database_name, star_expression4
    )
    response_star_expression5 = helpers.get_tables(
        client, database_name, star_expression5
    )
    response_star_expression6 = helpers.get_tables(
        client, database_name, star_expression6
    )

    tables_prefix = response_prefix["TableList"]
    tables_postfix = response_postfix["TableList"]
    tables_string_match = response_string_match["TableList"]
    tables_star_expression1 = response_star_expression1["TableList"]
    tables_star_expression2 = response_star_expression2["TableList"]
    tables_star_expression3 = response_star_expression3["TableList"]
    tables_star_expression4 = response_star_expression4["TableList"]
    tables_star_expression5 = response_star_expression5["TableList"]
    tables_star_expression6 = response_star_expression6["TableList"]

    assert len(tables_prefix) == 2
    assert len(tables_postfix) == 1
    assert len(tables_string_match) == 3
    assert len(tables_star_expression1) == 8
    assert len(tables_star_expression2) == 2
    assert len(tables_star_expression3) == 3
    assert len(tables_star_expression4) == 3
    assert len(tables_star_expression5) == 3
    assert len(tables_star_expression6) == 2


@mock_glue
def test_get_table_versions():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "myfirsttable"
    version_inputs = {}

    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)
    version_inputs["1"] = table_input

    # Get table should retrieve the first version
    table = client.get_table(DatabaseName=database_name, Name=table_name)["Table"]
    assert table["StorageDescriptor"]["Columns"] == []
    assert table["VersionId"] == "1"
    assert table["CatalogId"] == ACCOUNT_ID

    columns = [{"Name": "country", "Type": "string"}]
    table_input = helpers.create_table_input(database_name, table_name, columns=columns)
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["2"] = table_input

    # Updateing with an identical input should still create a new version
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["3"] = table_input

    response = helpers.get_table_versions(client, database_name, table_name)

    vers = response["TableVersions"]

    assert len(vers) == 3
    assert vers[0]["Table"]["StorageDescriptor"]["Columns"] == []
    assert vers[-1]["Table"]["StorageDescriptor"]["Columns"] == columns

    for n, ver in enumerate(vers):
        n = str(n + 1)
        assert ver["VersionId"] == n
        assert ver["Table"]["VersionId"] == n
        assert ver["Table"]["Name"] == table_name
        assert (
            ver["Table"]["StorageDescriptor"] == version_inputs[n]["StorageDescriptor"]
        )
        assert ver["Table"]["PartitionKeys"] == version_inputs[n]["PartitionKeys"]
        assert "UpdateTime" in ver["Table"]

    response = helpers.get_table_version(client, database_name, table_name, "3")
    ver = response["TableVersion"]

    assert ver["VersionId"] == "3"
    assert ver["Table"]["Name"] == table_name
    assert ver["Table"]["StorageDescriptor"]["Columns"] == columns

    # get_table should retrieve the latest version
    table = client.get_table(DatabaseName=database_name, Name=table_name)["Table"]
    assert table["StorageDescriptor"]["Columns"] == columns
    assert table["VersionId"] == "3"

    table = client.get_tables(DatabaseName=database_name)["TableList"][0]
    assert table["StorageDescriptor"]["Columns"] == columns
    assert table["VersionId"] == "3"


@mock_glue
def test_get_table_version_not_found():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.get_table_version(client, database_name, "myfirsttable", "20")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Version not found."


@mock_glue
def test_get_table_version_invalid_input():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.get_table_version(client, database_name, "myfirsttable", "10not-an-int")

    assert exc.value.response["Error"]["Code"] == "InvalidInputException"


@mock_glue
def test_delete_table_version():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "myfirsttable"
    version_inputs = {}

    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)
    version_inputs["1"] = table_input

    columns = [{"Name": "country", "Type": "string"}]
    table_input = helpers.create_table_input(database_name, table_name, columns=columns)
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["2"] = table_input

    # Updateing with an identical input should still create a new version
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["3"] = table_input

    response = helpers.get_table_versions(client, database_name, table_name)
    vers = response["TableVersions"]
    assert len(vers) == 3

    client.delete_table_version(
        DatabaseName=database_name, TableName=table_name, VersionId="2"
    )

    response = helpers.get_table_versions(client, database_name, table_name)
    vers = response["TableVersions"]
    assert len(vers) == 2
    assert [v["VersionId"] for v in vers] == ["1", "3"]


@mock_glue
def test_get_table_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, "myfirsttable")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Table myfirsttable not found."


@mock_glue
def test_get_table_when_database_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "nosuchdatabase"

    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, "myfirsttable")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert (
        exc.value.response["Error"]["Message"] == "Database nosuchdatabase not found."
    )


@mock_glue
def test_delete_table():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "myspecialtable"
    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)

    result = client.delete_table(DatabaseName=database_name, Name=table_name)
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200

    # confirm table is deleted
    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, table_name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Table myspecialtable not found."


@mock_glue
def test_batch_delete_table():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "myspecialtable"
    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)

    result = client.batch_delete_table(
        DatabaseName=database_name, TablesToDelete=[table_name]
    )
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200

    # confirm table is deleted
    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, table_name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert exc.value.response["Error"]["Message"] == "Table myspecialtable not found."


@mock_glue
def test_get_partitions_empty():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    assert len(response["Partitions"]) == 0


@mock_glue
def test_create_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    before = datetime.now(timezone.utc)

    part_input = helpers.create_partition_input(
        database_name, table_name, values=values
    )
    helpers.create_partition(client, database_name, table_name, part_input)

    after = datetime.now(timezone.utc)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    partitions = response["Partitions"]

    assert len(partitions) == 1

    partition = partitions[0]

    assert partition["TableName"] == table_name
    assert partition["StorageDescriptor"] == part_input["StorageDescriptor"]
    assert partition["Values"] == values
    assert partition["CreationTime"] > before
    assert partition["CreationTime"] < after


@mock_glue
def test_create_partition_already_exist():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    helpers.create_partition(client, database_name, table_name, values=values)

    with pytest.raises(ClientError) as exc:
        helpers.create_partition(client, database_name, table_name, values=values)

    assert exc.value.response["Error"]["Code"] == "AlreadyExistsException"


@mock_glue
def test_get_partition_not_found():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.get_partition(client, database_name, table_name, values)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert "partition" in exc.value.response["Error"]["Message"]


@mock_glue
def test_batch_create_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    before = datetime.now(timezone.utc)

    partition_inputs = []
    for i in range(0, 20):
        values = [f"2018-10-{i:2}"]
        part_input = helpers.create_partition_input(
            database_name, table_name, values=values
        )
        partition_inputs.append(part_input)

    client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=partition_inputs,
    )

    after = datetime.now(timezone.utc)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    partitions = response["Partitions"]

    assert len(partitions) == 20

    for idx, partition in enumerate(partitions):
        partition_input = partition_inputs[idx]

        assert partition["TableName"] == table_name
        assert partition["StorageDescriptor"] == partition_input["StorageDescriptor"]
        assert partition["Values"] == partition_input["Values"]
        assert partition["CreationTime"] > before
        assert partition["CreationTime"] < after


@mock_glue
def test_batch_create_partition_already_exist():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    helpers.create_partition(client, database_name, table_name, values=values)

    partition_input = helpers.create_partition_input(
        database_name, table_name, values=values
    )

    response = client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=[partition_input],
    )

    assert len(response["Errors"]) == 1
    assert response["Errors"][0]["PartitionValues"] == values
    assert response["Errors"][0]["ErrorDetail"]["ErrorCode"] == "AlreadyExistsException"


@mock_glue
def test_get_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    values = [["2018-10-01"], ["2018-09-01"]]

    helpers.create_partition(client, database_name, table_name, values=values[0])
    helpers.create_partition(client, database_name, table_name, values=values[1])

    response = client.get_partition(
        DatabaseName=database_name, TableName=table_name, PartitionValues=values[1]
    )

    partition = response["Partition"]

    assert partition["TableName"] == table_name
    assert partition["Values"] == values[1]


@mock_glue
def test_batch_get_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    values = [["2018-10-01"], ["2018-09-01"]]

    helpers.create_partition(client, database_name, table_name, values=values[0])
    helpers.create_partition(client, database_name, table_name, values=values[1])

    partitions_to_get = [{"Values": values[0]}, {"Values": values[1]}]
    response = client.batch_get_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionsToGet=partitions_to_get,
    )

    partitions = response["Partitions"]
    assert len(partitions) == 2

    partition = partitions[1]
    assert partition["TableName"] == table_name
    assert partition["Values"] == values[1]


@mock_glue
def test_batch_get_partition_missing_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    values = [["2018-10-01"], ["2018-09-01"], ["2018-08-01"]]

    helpers.create_partition(client, database_name, table_name, values=values[0])
    helpers.create_partition(client, database_name, table_name, values=values[2])

    partitions_to_get = [
        {"Values": values[0]},
        {"Values": values[1]},
        {"Values": values[2]},
    ]
    response = client.batch_get_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionsToGet=partitions_to_get,
    )

    partitions = response["Partitions"]
    assert len(partitions) == 2

    assert partitions[0]["Values"] == values[0]
    assert partitions[1]["Values"] == values[2]


@mock_glue
def test_update_partition_not_found_moving():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.update_partition(
            client,
            database_name,
            table_name,
            old_values=["0000-00-00"],
            values=["2018-10-02"],
        )

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert "partition" in exc.value.response["Error"]["Message"]


@mock_glue
def test_update_partition_not_found_change_in_place():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.update_partition(
            client, database_name, table_name, old_values=values, values=values
        )

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert "partition" in exc.value.response["Error"]["Message"]


@mock_glue
def test_update_partition_cannot_overwrite():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    values = [["2018-10-01"], ["2018-09-01"]]

    helpers.create_partition(client, database_name, table_name, values=values[0])
    helpers.create_partition(client, database_name, table_name, values=values[1])

    with pytest.raises(ClientError) as exc:
        helpers.update_partition(
            client, database_name, table_name, old_values=values[0], values=values[1]
        )

    assert exc.value.response["Error"]["Code"] == "AlreadyExistsException"


@mock_glue
def test_update_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)
    helpers.create_partition(client, database_name, table_name, values=values)

    response = helpers.update_partition(
        client,
        database_name,
        table_name,
        old_values=values,
        values=values,
        columns=[{"Name": "country", "Type": "string"}],
    )

    response = client.get_partition(
        DatabaseName=database_name, TableName=table_name, PartitionValues=values
    )
    partition = response["Partition"]

    assert partition["TableName"] == table_name
    assert partition["StorageDescriptor"]["Columns"] == [
        {"Name": "country", "Type": "string"}
    ]


@mock_glue
def test_update_partition_move():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    new_values = ["2018-09-01"]

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)
    helpers.create_partition(client, database_name, table_name, values=values)

    response = helpers.update_partition(
        client,
        database_name,
        table_name,
        old_values=values,
        values=new_values,
        columns=[{"Name": "country", "Type": "string"}],
    )

    with pytest.raises(ClientError) as exc:
        helpers.get_partition(client, database_name, table_name, values)

    # Old partition shouldn't exist anymore
    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"

    response = client.get_partition(
        DatabaseName=database_name, TableName=table_name, PartitionValues=new_values
    )
    partition = response["Partition"]

    assert partition["TableName"] == table_name
    assert partition["StorageDescriptor"]["Columns"] == [
        {"Name": "country", "Type": "string"}
    ]


@mock_glue
def test_batch_update_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"

    values = [
        ["2020-12-04"],
        ["2020-12-05"],
        ["2020-12-06"],
    ]

    new_values = [
        ["2020-11-04"],
        ["2020-11-05"],
        ["2020-11-06"],
    ]

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    batch_update_values = []
    for idx, value in enumerate(values):
        helpers.create_partition(client, database_name, table_name, values=value)
        batch_update_values.append(
            {
                "PartitionValueList": value,
                "PartitionInput": helpers.create_partition_input(
                    database_name,
                    table_name,
                    values=new_values[idx],
                    columns=[{"Name": "country", "Type": "string"}],
                ),
            }
        )

    response = client.batch_update_partition(
        DatabaseName=database_name, TableName=table_name, Entries=batch_update_values
    )

    for value in values:
        with pytest.raises(ClientError) as exc:
            helpers.get_partition(client, database_name, table_name, value)
        assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"

    for value in new_values:
        response = client.get_partition(
            DatabaseName=database_name, TableName=table_name, PartitionValues=value
        )
        partition = response["Partition"]

        assert partition["TableName"] == table_name
        assert partition["StorageDescriptor"]["Columns"] == [
            {"Name": "country", "Type": "string"}
        ]


@mock_glue
def test_batch_update_partition_missing_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"

    values = [
        ["2020-12-05"],
        ["2020-12-06"],
    ]

    new_values = [
        ["2020-11-05"],
        ["2020-11-06"],
    ]

    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    batch_update_values = []
    for idx, value in enumerate(values):
        helpers.create_partition(client, database_name, table_name, values=value)
        batch_update_values.append(
            {
                "PartitionValueList": value,
                "PartitionInput": helpers.create_partition_input(
                    database_name,
                    table_name,
                    values=new_values[idx],
                    columns=[{"Name": "country", "Type": "string"}],
                ),
            }
        )

    # add a non-existent partition to the batch update values
    batch_update_values.append(
        {
            "PartitionValueList": ["2020-10-10"],
            "PartitionInput": helpers.create_partition_input(
                database_name,
                table_name,
                values=["2019-09-09"],
                columns=[{"Name": "country", "Type": "string"}],
            ),
        }
    )

    response = client.batch_update_partition(
        DatabaseName=database_name, TableName=table_name, Entries=batch_update_values
    )

    assert len(response["Errors"]) == 1
    assert response["Errors"][0]["PartitionValueList"] == ["2020-10-10"]


@mock_glue
def test_delete_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    part_input = helpers.create_partition_input(
        database_name, table_name, values=values
    )
    helpers.create_partition(client, database_name, table_name, part_input)

    client.delete_partition(
        DatabaseName=database_name, TableName=table_name, PartitionValues=values
    )

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)
    partitions = response["Partitions"]
    assert partitions == []


@mock_glue
def test_delete_partition_bad_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        client.delete_partition(
            DatabaseName=database_name, TableName=table_name, PartitionValues=values
        )

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"


@mock_glue
def test_batch_delete_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    partition_inputs = []
    for i in range(0, 20):
        values = [f"2018-10-{i:2}"]
        part_input = helpers.create_partition_input(
            database_name, table_name, values=values
        )
        partition_inputs.append(part_input)

    client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=partition_inputs,
    )

    partition_values = [{"Values": p["Values"]} for p in partition_inputs]

    response = client.batch_delete_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionsToDelete=partition_values,
    )

    assert "Errors" not in response


@mock_glue
def test_batch_delete_partition_with_bad_partitions():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    partition_inputs = []
    for i in range(0, 20):
        values = [f"2018-10-{i:2}"]
        part_input = helpers.create_partition_input(
            database_name, table_name, values=values
        )
        partition_inputs.append(part_input)

    client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=partition_inputs,
    )

    partition_values = [{"Values": p["Values"]} for p in partition_inputs]

    partition_values.insert(5, {"Values": ["2018-11-01"]})
    partition_values.insert(10, {"Values": ["2018-11-02"]})
    partition_values.insert(15, {"Values": ["2018-11-03"]})

    response = client.batch_delete_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionsToDelete=partition_values,
    )

    assert len(response["Errors"]) == 3
    error_partitions = map(lambda x: x["PartitionValues"], response["Errors"])
    assert ["2018-11-01"] in error_partitions
    assert ["2018-11-02"] in error_partitions
    assert ["2018-11-03"] in error_partitions


@mock_glue
@freeze_time(FROZEN_CREATE_TIME)
def test_create_crawler_scheduled():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    role = "arn:aws:iam::123456789012:role/Glue/Role"
    database_name = "my_database_name"
    description = "my crawler description"
    targets = {
        "S3Targets": [{"Path": "s3://my-source-bucket/"}],
        "JdbcTargets": [],
        "MongoDBTargets": [],
        "DynamoDBTargets": [],
        "CatalogTargets": [],
    }
    schedule = "cron(15 12 * * ? *)"
    classifiers = []
    table_prefix = "my_table_prefix_"
    schema_change_policy = {
        "UpdateBehavior": "LOG",
        "DeleteBehavior": "LOG",
    }
    recrawl_policy = {"RecrawlBehavior": "CRAWL_NEW_FOLDERS_ONLY"}
    lineage_configuration = {"CrawlerLineageSettings": "DISABLE"}
    configuration = json.dumps(
        {
            "Version": 1.0,
            "CrawlerOutput": {
                "Partitions": {"AddOrUpdateBehavior": "InheritFromTable"},
            },
            "Grouping": {"TableGroupingPolicy": "CombineCompatibleSchemas"},
        }
    )
    crawler_security_configuration = "my_security_configuration"
    tags = {"tag_key": "tag_value"}
    helpers.create_crawler(
        client,
        name,
        role,
        targets,
        database_name=database_name,
        description=description,
        schedule=schedule,
        classifiers=classifiers,
        table_prefix=table_prefix,
        schema_change_policy=schema_change_policy,
        recrawl_policy=recrawl_policy,
        lineage_configuration=lineage_configuration,
        configuration=configuration,
        crawler_security_configuration=crawler_security_configuration,
        tags=tags,
    )

    response = client.get_crawler(Name=name)
    crawler = response["Crawler"]

    assert crawler.get("Name") == name
    assert crawler.get("Role") == role
    assert crawler.get("DatabaseName") == database_name
    assert crawler.get("Description") == description
    assert crawler.get("Targets") == targets
    assert crawler["Schedule"] == {"ScheduleExpression": schedule, "State": "SCHEDULED"}
    assert crawler.get("Classifiers") == classifiers
    assert crawler.get("TablePrefix") == table_prefix
    assert crawler.get("SchemaChangePolicy") == schema_change_policy
    assert crawler.get("RecrawlPolicy") == recrawl_policy
    assert crawler.get("LineageConfiguration") == lineage_configuration
    assert crawler.get("Configuration") == configuration
    assert crawler["CrawlerSecurityConfiguration"] == crawler_security_configuration

    assert crawler.get("State") == "READY"
    assert crawler.get("CrawlElapsedTime") == 0
    assert crawler.get("Version") == 1
    if not settings.TEST_SERVER_MODE:
        assert crawler["CreationTime"].timestamp() == FROZEN_CREATE_TIME.timestamp()
        assert crawler["LastUpdated"].timestamp() == FROZEN_CREATE_TIME.timestamp()

    assert "LastCrawl" not in crawler


@mock_glue
@freeze_time(FROZEN_CREATE_TIME)
def test_create_crawler_unscheduled():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    role = "arn:aws:iam::123456789012:role/Glue/Role"
    database_name = "my_database_name"
    description = "my crawler description"
    targets = {
        "S3Targets": [{"Path": "s3://my-source-bucket/"}],
        "JdbcTargets": [],
        "MongoDBTargets": [],
        "DynamoDBTargets": [],
        "CatalogTargets": [],
    }
    classifiers = []
    table_prefix = "my_table_prefix_"
    schema_change_policy = {
        "UpdateBehavior": "LOG",
        "DeleteBehavior": "LOG",
    }
    recrawl_policy = {"RecrawlBehavior": "CRAWL_NEW_FOLDERS_ONLY"}
    lineage_configuration = {"CrawlerLineageSettings": "DISABLE"}
    configuration = json.dumps(
        {
            "Version": 1.0,
            "CrawlerOutput": {
                "Partitions": {"AddOrUpdateBehavior": "InheritFromTable"},
            },
            "Grouping": {"TableGroupingPolicy": "CombineCompatibleSchemas"},
        }
    )
    crawler_security_configuration = "my_security_configuration"
    tags = {"tag_key": "tag_value"}
    helpers.create_crawler(
        client,
        name,
        role,
        targets,
        database_name=database_name,
        description=description,
        classifiers=classifiers,
        table_prefix=table_prefix,
        schema_change_policy=schema_change_policy,
        recrawl_policy=recrawl_policy,
        lineage_configuration=lineage_configuration,
        configuration=configuration,
        crawler_security_configuration=crawler_security_configuration,
        tags=tags,
    )

    response = client.get_crawler(Name=name)
    crawler = response["Crawler"]

    assert crawler.get("Name") == name
    assert crawler.get("Role") == role
    assert crawler.get("DatabaseName") == database_name
    assert crawler.get("Description") == description
    assert crawler.get("Targets") == targets
    assert "Schedule" not in crawler
    assert crawler.get("Classifiers") == classifiers
    assert crawler.get("TablePrefix") == table_prefix
    assert crawler.get("SchemaChangePolicy") == schema_change_policy
    assert crawler.get("RecrawlPolicy") == recrawl_policy
    assert crawler.get("LineageConfiguration") == lineage_configuration
    assert crawler.get("Configuration") == configuration
    assert crawler["CrawlerSecurityConfiguration"] == crawler_security_configuration

    assert crawler.get("State") == "READY"
    assert crawler.get("CrawlElapsedTime") == 0
    assert crawler.get("Version") == 1
    if not settings.TEST_SERVER_MODE:
        assert crawler["CreationTime"].timestamp() == FROZEN_CREATE_TIME.timestamp()
        assert crawler["LastUpdated"].timestamp() == FROZEN_CREATE_TIME.timestamp()

    assert "LastCrawl" not in crawler


@mock_glue
def test_create_crawler_already_exists():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    with pytest.raises(ClientError) as exc:
        helpers.create_crawler(client, name)

    assert exc.value.response["Error"]["Code"] == "AlreadyExistsException"


@mock_glue
def test_get_crawler_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"

    with pytest.raises(ClientError) as exc:
        client.get_crawler(Name=name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert (
        exc.value.response["Error"]["Message"] == "Crawler my_crawler_name not found."
    )


@mock_glue
def test_get_crawlers_empty():
    client = boto3.client("glue", region_name="us-east-1")
    response = client.get_crawlers()
    assert len(response["Crawlers"]) == 0


@mock_glue
def test_get_crawlers_several_items():
    client = boto3.client("glue", region_name="us-east-1")
    name_1, name_2 = "my_crawler_name_1", "my_crawler_name_2"

    helpers.create_crawler(client, name_1)
    helpers.create_crawler(client, name_2)

    crawlers = sorted(client.get_crawlers()["Crawlers"], key=lambda x: x["Name"])
    assert len(crawlers) == 2
    assert crawlers[0].get("Name") == name_1
    assert crawlers[1].get("Name") == name_2


@mock_glue
def test_start_crawler():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    client.start_crawler(Name=name)

    response = client.get_crawler(Name=name)
    crawler = response["Crawler"]

    assert crawler.get("State") == "RUNNING"


@mock_glue
def test_start_crawler_should_raise_exception_if_already_running():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    client.start_crawler(Name=name)
    with pytest.raises(ClientError) as exc:
        client.start_crawler(Name=name)

    assert exc.value.response["Error"]["Code"] == "CrawlerRunningException"


@mock_glue
def test_stop_crawler():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)
    client.start_crawler(Name=name)

    client.stop_crawler(Name=name)

    response = client.get_crawler(Name=name)
    crawler = response["Crawler"]

    assert crawler.get("State") == "STOPPING"


@mock_glue
def test_stop_crawler_should_raise_exception_if_not_running():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    with pytest.raises(ClientError) as exc:
        client.stop_crawler(Name=name)

    assert exc.value.response["Error"]["Code"] == "CrawlerNotRunningException"


@mock_glue
def test_delete_crawler():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    result = client.delete_crawler(Name=name)
    assert result["ResponseMetadata"]["HTTPStatusCode"] == 200

    # confirm crawler is deleted
    with pytest.raises(ClientError) as exc:
        client.get_crawler(Name=name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert (
        exc.value.response["Error"]["Message"] == "Crawler my_crawler_name not found."
    )


@mock_glue
def test_delete_crawler_not_exists():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"

    with pytest.raises(ClientError) as exc:
        client.delete_crawler(Name=name)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"
    assert (
        exc.value.response["Error"]["Message"] == "Crawler my_crawler_name not found."
    )
