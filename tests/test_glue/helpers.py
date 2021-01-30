from __future__ import unicode_literals

import copy

from .fixtures.datacatalog import TABLE_INPUT, PARTITION_INPUT, DATABASE_INPUT


def create_database_input(database_name):
    database_input = copy.deepcopy(DATABASE_INPUT)
    database_input["Name"] = database_name
    database_input["LocationUri"] = "s3://my-bucket/{database_name}".format(
        database_name=database_name
    )
    return database_input


def create_database(client, database_name, database_input=None):
    if database_input is None:
        database_input = create_database_input(database_name)
    return client.create_database(DatabaseInput=database_input)


def get_database(client, database_name):
    return client.get_database(Name=database_name)


def create_table_input(database_name, table_name, columns=[], partition_keys=[]):
    table_input = copy.deepcopy(TABLE_INPUT)
    table_input["Name"] = table_name
    table_input["PartitionKeys"] = partition_keys
    table_input["StorageDescriptor"]["Columns"] = columns
    table_input["StorageDescriptor"][
        "Location"
    ] = "s3://my-bucket/{database_name}/{table_name}".format(
        database_name=database_name, table_name=table_name
    )
    return table_input


def create_table(client, database_name, table_name, table_input=None, **kwargs):
    if table_input is None:
        table_input = create_table_input(database_name, table_name, **kwargs)

    return client.create_table(DatabaseName=database_name, TableInput=table_input)


def update_table(client, database_name, table_name, table_input=None, **kwargs):
    if table_input is None:
        table_input = create_table_input(database_name, table_name, **kwargs)

    return client.update_table(DatabaseName=database_name, TableInput=table_input)


def get_table(client, database_name, table_name):
    return client.get_table(DatabaseName=database_name, Name=table_name)


def get_tables(client, database_name):
    return client.get_tables(DatabaseName=database_name)


def get_table_versions(client, database_name, table_name):
    return client.get_table_versions(DatabaseName=database_name, TableName=table_name)


def get_table_version(client, database_name, table_name, version_id):
    return client.get_table_version(
        DatabaseName=database_name, TableName=table_name, VersionId=version_id
    )


def create_partition_input(database_name, table_name, values=[], columns=[]):
    root_path = "s3://my-bucket/{database_name}/{table_name}".format(
        database_name=database_name, table_name=table_name
    )

    part_input = copy.deepcopy(PARTITION_INPUT)
    part_input["Values"] = values
    part_input["StorageDescriptor"]["Columns"] = columns
    part_input["StorageDescriptor"]["SerdeInfo"]["Parameters"]["path"] = root_path
    return part_input


def create_partition(client, database_name, table_name, partiton_input=None, **kwargs):
    if partiton_input is None:
        partiton_input = create_partition_input(database_name, table_name, **kwargs)
    return client.create_partition(
        DatabaseName=database_name, TableName=table_name, PartitionInput=partiton_input
    )


def update_partition(
    client, database_name, table_name, old_values=[], partiton_input=None, **kwargs
):
    if partiton_input is None:
        partiton_input = create_partition_input(database_name, table_name, **kwargs)
    return client.update_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInput=partiton_input,
        PartitionValueList=old_values,
    )


def get_partition(client, database_name, table_name, values):
    return client.get_partition(
        DatabaseName=database_name, TableName=table_name, PartitionValues=values
    )
