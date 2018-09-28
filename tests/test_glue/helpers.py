from __future__ import unicode_literals

import copy

from .fixtures.datacatalog import TABLE_INPUT


def create_database(client, database_name):
    return client.create_database(
        DatabaseInput={
            'Name': database_name
        }
    )


def get_database(client, database_name):
    return client.get_database(Name=database_name)


def create_table_input(table_name, s3_location, columns=[], partition_keys=[]):
    table_input = copy.deepcopy(TABLE_INPUT)
    table_input['Name'] = table_name
    table_input['PartitionKeys'] = partition_keys
    table_input['StorageDescriptor']['Columns'] = columns
    table_input['StorageDescriptor']['Location'] = s3_location
    return table_input


def create_table(client, database_name, table_name, table_input):
    return client.create_table(
        DatabaseName=database_name,
        TableInput=table_input
    )


def get_table(client, database_name, table_name):
    return client.get_table(
        DatabaseName=database_name,
        Name=table_name
    )


def get_tables(client, database_name):
    return client.get_tables(
        DatabaseName=database_name
    )
