import sure  # noqa # pylint: disable=unused-import
import re
import pytest
import json
import boto3
from botocore.client import ClientError


from datetime import datetime
import pytz
from freezegun import freeze_time

from moto import mock_glue, settings
from . import helpers


FROZEN_CREATE_TIME = datetime(2015, 1, 1, 0, 0, 0)


@mock_glue
@freeze_time(FROZEN_CREATE_TIME)
def test_create_database():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    database_input = helpers.create_database_input(database_name)
    helpers.create_database(client, database_name, database_input)

    response = helpers.get_database(client, database_name)
    database = response["Database"]

    database.get("Name").should.equal(database_name)
    database.get("Description").should.equal(database_input.get("Description"))
    database.get("LocationUri").should.equal(database_input.get("LocationUri"))
    database.get("Parameters").should.equal(database_input.get("Parameters"))
    if not settings.TEST_SERVER_MODE:
        database.get("CreateTime").should.equal(FROZEN_CREATE_TIME)
    database.get("CreateTableDefaultPermissions").should.equal(
        database_input.get("CreateTableDefaultPermissions")
    )
    database.get("TargetDatabase").should.equal(database_input.get("TargetDatabase"))
    database.get("CatalogId").should.equal(database_input.get("CatalogId"))


@mock_glue
def test_create_database_already_exists():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "cantcreatethisdatabasetwice"
    helpers.create_database(client, database_name)

    with pytest.raises(ClientError) as exc:
        helpers.create_database(client, database_name)

    exc.value.response["Error"]["Code"].should.equal("AlreadyExistsException")


@mock_glue
def test_get_database_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "nosuchdatabase"

    with pytest.raises(ClientError) as exc:
        helpers.get_database(client, database_name)

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match(
        "Database nosuchdatabase not found"
    )


@mock_glue
def test_get_databases_empty():
    client = boto3.client("glue", region_name="us-east-1")
    response = client.get_databases()
    response["DatabaseList"].should.have.length_of(0)


@mock_glue
def test_get_databases_several_items():
    client = boto3.client("glue", region_name="us-east-1")
    database_name_1, database_name_2 = "firstdatabase", "seconddatabase"

    helpers.create_database(client, database_name_1, {"Name": database_name_1})
    helpers.create_database(client, database_name_2, {"Name": database_name_2})

    database_list = sorted(
        client.get_databases()["DatabaseList"], key=lambda x: x["Name"]
    )
    database_list.should.have.length_of(2)
    database_list[0]["Name"].should.equal(database_name_1)
    database_list[1]["Name"].should.equal(database_name_2)


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
    [db["Name"] for db in database_list].should.equal([database_name_2])


@mock_glue
def test_delete_unknown_database():
    client = boto3.client("glue", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_database(Name="x")
    err = exc.value.response["Error"]
    err["Code"].should.equal("EntityNotFoundException")
    err["Message"].should.equal("Database x not found.")


@mock_glue
def test_create_table():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "myspecialtable"
    table_input = helpers.create_table_input(database_name, table_name)
    helpers.create_table(client, database_name, table_name, table_input)

    response = helpers.get_table(client, database_name, table_name)
    table = response["Table"]

    table["Name"].should.equal(table_input["Name"])
    table["StorageDescriptor"].should.equal(table_input["StorageDescriptor"])
    table["PartitionKeys"].should.equal(table_input["PartitionKeys"])


@mock_glue
def test_create_table_already_exists():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    table_name = "cantcreatethistabletwice"
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.create_table(client, database_name, table_name)

    exc.value.response["Error"]["Code"].should.equal("AlreadyExistsException")


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

    tables.should.have.length_of(3)

    for table in tables:
        table_name = table["Name"]
        table_name.should.equal(table_inputs[table_name]["Name"])
        table["StorageDescriptor"].should.equal(
            table_inputs[table_name]["StorageDescriptor"]
        )
        table["PartitionKeys"].should.equal(table_inputs[table_name]["PartitionKeys"])


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

    columns = [{"Name": "country", "Type": "string"}]
    table_input = helpers.create_table_input(database_name, table_name, columns=columns)
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["2"] = table_input

    # Updateing with an identical input should still create a new version
    helpers.update_table(client, database_name, table_name, table_input)
    version_inputs["3"] = table_input

    response = helpers.get_table_versions(client, database_name, table_name)

    vers = response["TableVersions"]

    vers.should.have.length_of(3)
    vers[0]["Table"]["StorageDescriptor"]["Columns"].should.equal([])
    vers[-1]["Table"]["StorageDescriptor"]["Columns"].should.equal(columns)

    for n, ver in enumerate(vers):
        n = str(n + 1)
        ver["VersionId"].should.equal(n)
        ver["Table"]["Name"].should.equal(table_name)
        ver["Table"]["StorageDescriptor"].should.equal(
            version_inputs[n]["StorageDescriptor"]
        )
        ver["Table"]["PartitionKeys"].should.equal(version_inputs[n]["PartitionKeys"])

    response = helpers.get_table_version(client, database_name, table_name, "3")
    ver = response["TableVersion"]

    ver["VersionId"].should.equal("3")
    ver["Table"]["Name"].should.equal(table_name)
    ver["Table"]["StorageDescriptor"]["Columns"].should.equal(columns)


@mock_glue
def test_get_table_version_not_found():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.get_table_version(client, database_name, "myfirsttable", "20")

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match("version", re.I)


@mock_glue
def test_get_table_version_invalid_input():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    with pytest.raises(ClientError) as exc:
        helpers.get_table_version(client, database_name, "myfirsttable", "10not-an-int")

    exc.value.response["Error"]["Code"].should.equal("InvalidInputException")


@mock_glue
def test_get_table_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    helpers.create_database(client, database_name)

    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, "myfirsttable")

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match("Table myfirsttable not found")


@mock_glue
def test_get_table_when_database_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "nosuchdatabase"

    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, "myfirsttable")

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match(
        "Database nosuchdatabase not found"
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
    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # confirm table is deleted
    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, table_name)

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match(
        "Table myspecialtable not found"
    )


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
    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # confirm table is deleted
    with pytest.raises(ClientError) as exc:
        helpers.get_table(client, database_name, table_name)

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match(
        "Table myspecialtable not found"
    )


@mock_glue
def test_get_partitions_empty():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    response["Partitions"].should.have.length_of(0)


@mock_glue
def test_create_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    values = ["2018-10-01"]
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    before = datetime.now(pytz.utc)

    part_input = helpers.create_partition_input(
        database_name, table_name, values=values
    )
    helpers.create_partition(client, database_name, table_name, part_input)

    after = datetime.now(pytz.utc)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    partitions = response["Partitions"]

    partitions.should.have.length_of(1)

    partition = partitions[0]

    partition["TableName"].should.equal(table_name)
    partition["StorageDescriptor"].should.equal(part_input["StorageDescriptor"])
    partition["Values"].should.equal(values)
    partition["CreationTime"].should.be.greater_than(before)
    partition["CreationTime"].should.be.lower_than(after)


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

    exc.value.response["Error"]["Code"].should.equal("AlreadyExistsException")


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

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match("partition")


@mock_glue
def test_batch_create_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)

    helpers.create_table(client, database_name, table_name)

    before = datetime.now(pytz.utc)

    partition_inputs = []
    for i in range(0, 20):
        values = ["2018-10-{:2}".format(i)]
        part_input = helpers.create_partition_input(
            database_name, table_name, values=values
        )
        partition_inputs.append(part_input)

    client.batch_create_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=partition_inputs,
    )

    after = datetime.now(pytz.utc)

    response = client.get_partitions(DatabaseName=database_name, TableName=table_name)

    partitions = response["Partitions"]

    partitions.should.have.length_of(20)

    for idx, partition in enumerate(partitions):
        partition_input = partition_inputs[idx]

        partition["TableName"].should.equal(table_name)
        partition["StorageDescriptor"].should.equal(
            partition_input["StorageDescriptor"]
        )
        partition["Values"].should.equal(partition_input["Values"])
        partition["CreationTime"].should.be.greater_than(before)
        partition["CreationTime"].should.be.lower_than(after)


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

    response.should.have.key("Errors")
    response["Errors"].should.have.length_of(1)
    response["Errors"][0]["PartitionValues"].should.equal(values)
    response["Errors"][0]["ErrorDetail"]["ErrorCode"].should.equal(
        "AlreadyExistsException"
    )


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

    partition["TableName"].should.equal(table_name)
    partition["Values"].should.equal(values[1])


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
    partitions.should.have.length_of(2)

    partition = partitions[1]
    partition["TableName"].should.equal(table_name)
    partition["Values"].should.equal(values[1])


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
    partitions.should.have.length_of(2)

    partitions[0]["Values"].should.equal(values[0])
    partitions[1]["Values"].should.equal(values[2])


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

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match("partition")


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

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match("partition")


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

    exc.value.response["Error"]["Code"].should.equal("AlreadyExistsException")


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

    partition["TableName"].should.equal(table_name)
    partition["StorageDescriptor"]["Columns"].should.equal(
        [{"Name": "country", "Type": "string"}]
    )


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
    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")

    response = client.get_partition(
        DatabaseName=database_name, TableName=table_name, PartitionValues=new_values
    )
    partition = response["Partition"]

    partition["TableName"].should.equal(table_name)
    partition["StorageDescriptor"]["Columns"].should.equal(
        [{"Name": "country", "Type": "string"}]
    )


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
        DatabaseName=database_name, TableName=table_name, Entries=batch_update_values,
    )

    for value in values:
        with pytest.raises(ClientError) as exc:
            helpers.get_partition(client, database_name, table_name, value)
        exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")

    for value in new_values:
        response = client.get_partition(
            DatabaseName=database_name, TableName=table_name, PartitionValues=value
        )
        partition = response["Partition"]

        partition["TableName"].should.equal(table_name)
        partition["StorageDescriptor"]["Columns"].should.equal(
            [{"Name": "country", "Type": "string"}]
        )


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
        DatabaseName=database_name, TableName=table_name, Entries=batch_update_values,
    )

    response.should.have.key("Errors")
    response["Errors"].should.have.length_of(1)
    response["Errors"][0]["PartitionValueList"].should.equal(["2020-10-10"])


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
    partitions.should.be.empty


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

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")


@mock_glue
def test_batch_delete_partition():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    partition_inputs = []
    for i in range(0, 20):
        values = ["2018-10-{:2}".format(i)]
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

    response.should_not.have.key("Errors")


@mock_glue
def test_batch_delete_partition_with_bad_partitions():
    client = boto3.client("glue", region_name="us-east-1")
    database_name = "myspecialdatabase"
    table_name = "myfirsttable"
    helpers.create_database(client, database_name)
    helpers.create_table(client, database_name, table_name)

    partition_inputs = []
    for i in range(0, 20):
        values = ["2018-10-{:2}".format(i)]
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

    response.should.have.key("Errors")
    response["Errors"].should.have.length_of(3)
    error_partitions = map(lambda x: x["PartitionValues"], response["Errors"])
    ["2018-11-01"].should.be.within(error_partitions)
    ["2018-11-02"].should.be.within(error_partitions)
    ["2018-11-03"].should.be.within(error_partitions)


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

    crawler.get("Name").should.equal(name)
    crawler.get("Role").should.equal(role)
    crawler.get("DatabaseName").should.equal(database_name)
    crawler.get("Description").should.equal(description)
    crawler.get("Targets").should.equal(targets)
    crawler.get("Schedule").should.equal(
        {"ScheduleExpression": schedule, "State": "SCHEDULED"}
    )
    crawler.get("Classifiers").should.equal(classifiers)
    crawler.get("TablePrefix").should.equal(table_prefix)
    crawler.get("SchemaChangePolicy").should.equal(schema_change_policy)
    crawler.get("RecrawlPolicy").should.equal(recrawl_policy)
    crawler.get("LineageConfiguration").should.equal(lineage_configuration)
    crawler.get("Configuration").should.equal(configuration)
    crawler.get("CrawlerSecurityConfiguration").should.equal(
        crawler_security_configuration
    )

    crawler.get("State").should.equal("READY")
    crawler.get("CrawlElapsedTime").should.equal(0)
    crawler.get("Version").should.equal(1)
    if not settings.TEST_SERVER_MODE:
        crawler.get("CreationTime").should.equal(FROZEN_CREATE_TIME)
        crawler.get("LastUpdated").should.equal(FROZEN_CREATE_TIME)

    crawler.should.not_have.key("LastCrawl")


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

    crawler.get("Name").should.equal(name)
    crawler.get("Role").should.equal(role)
    crawler.get("DatabaseName").should.equal(database_name)
    crawler.get("Description").should.equal(description)
    crawler.get("Targets").should.equal(targets)
    crawler.should.not_have.key("Schedule")
    crawler.get("Classifiers").should.equal(classifiers)
    crawler.get("TablePrefix").should.equal(table_prefix)
    crawler.get("SchemaChangePolicy").should.equal(schema_change_policy)
    crawler.get("RecrawlPolicy").should.equal(recrawl_policy)
    crawler.get("LineageConfiguration").should.equal(lineage_configuration)
    crawler.get("Configuration").should.equal(configuration)
    crawler.get("CrawlerSecurityConfiguration").should.equal(
        crawler_security_configuration
    )

    crawler.get("State").should.equal("READY")
    crawler.get("CrawlElapsedTime").should.equal(0)
    crawler.get("Version").should.equal(1)
    if not settings.TEST_SERVER_MODE:
        crawler.get("CreationTime").should.equal(FROZEN_CREATE_TIME)
        crawler.get("LastUpdated").should.equal(FROZEN_CREATE_TIME)

    crawler.should.not_have.key("LastCrawl")


@mock_glue
def test_create_crawler_already_exists():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    with pytest.raises(ClientError) as exc:
        helpers.create_crawler(client, name)

    exc.value.response["Error"]["Code"].should.equal("AlreadyExistsException")


@mock_glue
def test_get_crawler_not_exits():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"

    with pytest.raises(ClientError) as exc:
        client.get_crawler(Name=name)

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match(
        "Crawler my_crawler_name not found"
    )


@mock_glue
def test_get_crawlers_empty():
    client = boto3.client("glue", region_name="us-east-1")
    response = client.get_crawlers()
    response["Crawlers"].should.have.length_of(0)


@mock_glue
def test_get_crawlers_several_items():
    client = boto3.client("glue", region_name="us-east-1")
    name_1, name_2 = "my_crawler_name_1", "my_crawler_name_2"

    helpers.create_crawler(client, name_1)
    helpers.create_crawler(client, name_2)

    crawlers = sorted(client.get_crawlers()["Crawlers"], key=lambda x: x["Name"])
    crawlers.should.have.length_of(2)
    crawlers[0].get("Name").should.equal(name_1)
    crawlers[1].get("Name").should.equal(name_2)


@mock_glue
def test_start_crawler():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    client.start_crawler(Name=name)

    response = client.get_crawler(Name=name)
    crawler = response["Crawler"]

    crawler.get("State").should.equal("RUNNING")


@mock_glue
def test_start_crawler_should_raise_exception_if_already_running():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    client.start_crawler(Name=name)
    with pytest.raises(ClientError) as exc:
        client.start_crawler(Name=name)

    exc.value.response["Error"]["Code"].should.equal("CrawlerRunningException")


@mock_glue
def test_stop_crawler():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)
    client.start_crawler(Name=name)

    client.stop_crawler(Name=name)

    response = client.get_crawler(Name=name)
    crawler = response["Crawler"]

    crawler.get("State").should.equal("STOPPING")


@mock_glue
def test_stop_crawler_should_raise_exception_if_not_running():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    with pytest.raises(ClientError) as exc:
        client.stop_crawler(Name=name)

    exc.value.response["Error"]["Code"].should.equal("CrawlerNotRunningException")


@mock_glue
def test_delete_crawler():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"
    helpers.create_crawler(client, name)

    result = client.delete_crawler(Name=name)
    result["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    # confirm crawler is deleted
    with pytest.raises(ClientError) as exc:
        client.get_crawler(Name=name)

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match(
        "Crawler my_crawler_name not found"
    )


@mock_glue
def test_delete_crawler_not_exists():
    client = boto3.client("glue", region_name="us-east-1")
    name = "my_crawler_name"

    with pytest.raises(ClientError) as exc:
        client.delete_crawler(Name=name)

    exc.value.response["Error"]["Code"].should.equal("EntityNotFoundException")
    exc.value.response["Error"]["Message"].should.match(
        "Crawler my_crawler_name not found"
    )
