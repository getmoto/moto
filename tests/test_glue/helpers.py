import copy

from .fixtures.datacatalog import TABLE_INPUT, PARTITION_INPUT, DATABASE_INPUT
from .fixtures.schema_registry import (
    TEST_REGISTRY_NAME,
    TEST_SCHEMA_NAME,
    TEST_BACKWARD_COMPATIBILITY,
    TEST_AVRO_DATA_FORMAT,
    TEST_AVRO_SCHEMA_DEFINITION,
    TEST_SCHEMA_ID,
    TEST_NEW_AVRO_SCHEMA_DEFINITION,
)


def create_database_input(database_name):
    database_input = copy.deepcopy(DATABASE_INPUT)
    database_input["Name"] = database_name
    database_input["LocationUri"] = f"s3://my-bucket/{database_name}"
    return database_input


def create_database(client, database_name, database_input=None, catalog_id=None):
    if database_input is None:
        database_input = create_database_input(database_name)

    database_kwargs = {"DatabaseInput": database_input}
    if catalog_id is not None:
        database_kwargs["CatalogId"] = catalog_id
    return client.create_database(**database_kwargs)


def get_database(client, database_name):
    return client.get_database(Name=database_name)


def create_table_input(database_name, table_name, columns=None, partition_keys=None):
    table_input = copy.deepcopy(TABLE_INPUT)
    table_input["Name"] = table_name
    table_input["PartitionKeys"] = partition_keys or []
    table_input["StorageDescriptor"]["Columns"] = columns or []
    table_input["StorageDescriptor"][
        "Location"
    ] = f"s3://my-bucket/{database_name}/{table_name}"
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


def get_tables(client, database_name, expression=None):
    if expression:
        return client.get_tables(DatabaseName=database_name, Expression=expression)
    else:
        return client.get_tables(DatabaseName=database_name)


def get_table_versions(client, database_name, table_name):
    return client.get_table_versions(DatabaseName=database_name, TableName=table_name)


def get_table_version(client, database_name, table_name, version_id):
    return client.get_table_version(
        DatabaseName=database_name, TableName=table_name, VersionId=version_id
    )


def create_column(name, type_, comment=None, parameters=None):
    column = {"Name": name, "Type": type_}
    if comment is not None:
        column["Comment"] = comment
    if parameters is not None:
        column["Parameters"] = parameters
    return column


def create_partition_input(database_name, table_name, values=None, columns=None):
    root_path = f"s3://my-bucket/{database_name}/{table_name}"

    part_input = copy.deepcopy(PARTITION_INPUT)
    part_input["Values"] = values or []
    part_input["StorageDescriptor"]["Columns"] = columns or []
    part_input["StorageDescriptor"]["SerdeInfo"]["Parameters"]["path"] = root_path
    return part_input


def create_partition(client, database_name, table_name, partiton_input=None, **kwargs):
    if partiton_input is None:
        partiton_input = create_partition_input(database_name, table_name, **kwargs)
    return client.create_partition(
        DatabaseName=database_name, TableName=table_name, PartitionInput=partiton_input
    )


def update_partition(
    client, database_name, table_name, old_values=None, partiton_input=None, **kwargs
):
    if partiton_input is None:
        partiton_input = create_partition_input(database_name, table_name, **kwargs)
    return client.update_partition(
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInput=partiton_input,
        PartitionValueList=old_values or [],
    )


def get_partition(client, database_name, table_name, values):
    return client.get_partition(
        DatabaseName=database_name, TableName=table_name, PartitionValues=values
    )


def create_crawler(
    client, crawler_name, crawler_role=None, crawler_targets=None, **kwargs
):
    optional_param_map = {
        "database_name": "DatabaseName",
        "description": "Description",
        "schedule": "Schedule",
        "classifiers": "Classifiers",
        "table_prefix": "TablePrefix",
        "schema_change_policy": "SchemaChangePolicy",
        "recrawl_policy": "RecrawlPolicy",
        "lineage_configuration": "LineageConfiguration",
        "configuration": "Configuration",
        "crawler_security_configuration": "CrawlerSecurityConfiguration",
        "tags": "Tags",
    }

    params = {
        boto3_key: kwargs.get(key)
        for key, boto3_key in optional_param_map.items()
        if kwargs.get(key) is not None
    }

    if crawler_role is None:
        crawler_role = "arn:aws:iam::123456789012:role/Glue/Role"

    if crawler_targets is None:
        crawler_targets = {
            "S3Targets": [],
            "JdbcTargets": [],
            "MongoDBTargets": [],
            "DynamoDBTargets": [],
            "CatalogTargets": [],
        }

    return client.create_crawler(
        Name=crawler_name, Role=crawler_role, Targets=crawler_targets, **params
    )


def create_registry(client, registry_name=TEST_REGISTRY_NAME):
    return client.create_registry(RegistryName=registry_name)


def create_schema(
    client,
    registry_id,
    data_format=TEST_AVRO_DATA_FORMAT,
    compatibility=TEST_BACKWARD_COMPATIBILITY,
    schema_definition=TEST_AVRO_SCHEMA_DEFINITION,
):
    return client.create_schema(
        RegistryId=registry_id,
        SchemaName=TEST_SCHEMA_NAME,
        DataFormat=data_format,
        Compatibility=compatibility,
        SchemaDefinition=schema_definition,
    )


def register_schema_version(client):
    return client.register_schema_version(
        SchemaId=TEST_SCHEMA_ID, SchemaDefinition=TEST_NEW_AVRO_SCHEMA_DEFINITION
    )
