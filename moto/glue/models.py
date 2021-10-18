from __future__ import unicode_literals

import time
from datetime import datetime

from moto.core import BaseBackend, BaseModel
from collections import OrderedDict
from .exceptions import (
    JsonRESTError,
    CrawlerAlreadyExistsException,
    CrawlerNotFoundException,
    DatabaseAlreadyExistsException,
    DatabaseNotFoundException,
    TableAlreadyExistsException,
    TableNotFoundException,
    PartitionAlreadyExistsException,
    PartitionNotFoundException,
    VersionNotFoundException,
)


class GlueBackend(BaseBackend):
    def __init__(self):
        self.databases = OrderedDict()
        self.crawlers = OrderedDict()

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "glue"
        )

    def create_database(self, database_name, database_input):
        if database_name in self.databases:
            raise DatabaseAlreadyExistsException()

        database = FakeDatabase(database_name, database_input)
        self.databases[database_name] = database
        return database

    def get_database(self, database_name):
        try:
            return self.databases[database_name]
        except KeyError:
            raise DatabaseNotFoundException(database_name)

    def get_databases(self):
        return [self.databases[key] for key in self.databases] if self.databases else []

    def create_table(self, database_name, table_name, table_input):
        database = self.get_database(database_name)

        if table_name in database.tables:
            raise TableAlreadyExistsException()

        table = FakeTable(database_name, table_name, table_input)
        database.tables[table_name] = table
        return table

    def get_table(self, database_name, table_name):
        database = self.get_database(database_name)
        try:
            return database.tables[table_name]
        except KeyError:
            raise TableNotFoundException(table_name)

    def get_tables(self, database_name):
        database = self.get_database(database_name)
        return [table for table_name, table in database.tables.items()]

    def delete_table(self, database_name, table_name):
        database = self.get_database(database_name)
        try:
            del database.tables[table_name]
        except KeyError:
            raise TableNotFoundException(table_name)
        return {}

    def create_crawler(
        self,
        name,
        role,
        database_name,
        description,
        targets,
        schedule,
        classifiers,
        table_prefix,
        schema_change_policy,
        recrawl_policy,
        lineage_configuration,
        configuration,
        crawler_security_configuration,
        tags,
    ):
        if name in self.crawlers:
            raise CrawlerAlreadyExistsException()

        crawler = FakeCrawler(
            name=name,
            role=role,
            database_name=database_name,
            description=description,
            targets=targets,
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
        self.crawlers[name] = crawler

    def get_crawler(self, name):
        try:
            return self.crawlers[name]
        except KeyError:
            raise CrawlerNotFoundException(name)

    def get_crawlers(self):
        return [self.crawlers[key] for key in self.crawlers] if self.crawlers else []

    def delete_crawler(self, name):
        try:
            del self.crawlers[name]
        except KeyError:
            raise CrawlerNotFoundException(name)


class FakeDatabase(BaseModel):
    def __init__(self, database_name, database_input):
        self.name = database_name
        self.input = database_input
        self.created_time = datetime.utcnow()
        self.tables = OrderedDict()

    def as_dict(self):
        return {
            "Name": self.name,
            "Description": self.input.get("Description"),
            "LocationUri": self.input.get("LocationUri"),
            "Parameters": self.input.get("Parameters"),
            "CreateTime": self.created_time.isoformat(),
            "CreateTableDefaultPermissions": self.input.get(
                "CreateTableDefaultPermissions"
            ),
            "TargetDatabase": self.input.get("TargetDatabase"),
            "CatalogId": self.input.get("CatalogId"),
        }


class FakeTable(BaseModel):
    def __init__(self, database_name, table_name, table_input):
        self.database_name = database_name
        self.name = table_name
        self.partitions = OrderedDict()
        self.versions = []
        self.update(table_input)

    def update(self, table_input):
        self.versions.append(table_input)

    def get_version(self, ver):
        try:
            if not isinstance(ver, int):
                # "1" goes to [0]
                ver = int(ver) - 1
        except ValueError as e:
            raise JsonRESTError("InvalidInputException", str(e))

        try:
            return self.versions[ver]
        except IndexError:
            raise VersionNotFoundException()

    def as_dict(self, version=-1):
        obj = {"DatabaseName": self.database_name, "Name": self.name}
        obj.update(self.get_version(version))
        return obj

    def create_partition(self, partiton_input):
        partition = FakePartition(self.database_name, self.name, partiton_input)
        key = str(partition.values)
        if key in self.partitions:
            raise PartitionAlreadyExistsException()
        self.partitions[str(partition.values)] = partition

    def get_partitions(self):
        return [p for str_part_values, p in self.partitions.items()]

    def get_partition(self, values):
        try:
            return self.partitions[str(values)]
        except KeyError:
            raise PartitionNotFoundException()

    def update_partition(self, old_values, partiton_input):
        partition = FakePartition(self.database_name, self.name, partiton_input)
        key = str(partition.values)
        if old_values == partiton_input["Values"]:
            # Altering a partition in place. Don't remove it so the order of
            # returned partitions doesn't change
            if key not in self.partitions:
                raise PartitionNotFoundException()
        else:
            removed = self.partitions.pop(str(old_values), None)
            if removed is None:
                raise PartitionNotFoundException()
            if key in self.partitions:
                # Trying to update to overwrite a partition that exists
                raise PartitionAlreadyExistsException()
        self.partitions[key] = partition

    def delete_partition(self, values):
        try:
            del self.partitions[str(values)]
        except KeyError:
            raise PartitionNotFoundException()


class FakePartition(BaseModel):
    def __init__(self, database_name, table_name, partiton_input):
        self.creation_time = time.time()
        self.database_name = database_name
        self.table_name = table_name
        self.partition_input = partiton_input
        self.values = self.partition_input.get("Values", [])

    def as_dict(self):
        obj = {
            "DatabaseName": self.database_name,
            "TableName": self.table_name,
            "CreationTime": self.creation_time,
        }
        obj.update(self.partition_input)
        return obj


class FakeCrawler(BaseModel):
    def __init__(
        self,
        name,
        role,
        database_name,
        description,
        targets,
        schedule,
        classifiers,
        table_prefix,
        schema_change_policy,
        recrawl_policy,
        lineage_configuration,
        configuration,
        crawler_security_configuration,
        tags,
    ):
        self.name = name
        self.role = role
        self.database_name = database_name
        self.description = description
        self.targets = targets
        self.schedule = schedule
        self.classifiers = classifiers
        self.table_prefix = table_prefix
        self.schema_change_policy = schema_change_policy
        self.recrawl_policy = recrawl_policy
        self.lineage_configuration = lineage_configuration
        self.configuration = configuration
        self.crawler_security_configuration = crawler_security_configuration
        self.tags = tags
        self.state = "READY"
        self.creation_time = datetime.utcnow()
        self.last_updated = self.creation_time
        self.version = 1
        self.crawl_elapsed_time = 0
        self.last_crawl_info = None

    def as_dict(self):
        last_crawl = self.last_crawl_info.as_dict() if self.last_crawl_info else None
        data = {
            "Name": self.name,
            "Role": self.role,
            "Targets": self.targets,
            "DatabaseName": self.database_name,
            "Description": self.description,
            "Classifiers": self.classifiers,
            "RecrawlPolicy": self.recrawl_policy,
            "SchemaChangePolicy": self.schema_change_policy,
            "LineageConfiguration": self.lineage_configuration,
            "State": self.state,
            "TablePrefix": self.table_prefix,
            "CrawlElapsedTime": self.crawl_elapsed_time,
            "CreationTime": self.creation_time.isoformat(),
            "LastUpdated": self.last_updated.isoformat(),
            "LastCrawl": last_crawl,
            "Version": self.version,
            "Configuration": self.configuration,
            "CrawlerSecurityConfiguration": self.crawler_security_configuration,
        }

        if self.schedule:
            data["Schedule"] = {
                "ScheduleExpression": self.schedule,
                "State": "SCHEDULED",
            }

        if self.last_crawl_info:
            data["LastCrawl"] = self.last_crawl_info.as_dict()

        return data


class LastCrawlInfo(BaseModel):
    def __init__(
        self, error_message, log_group, log_stream, message_prefix, start_time, status,
    ):
        self.error_message = error_message
        self.log_group = log_group
        self.log_stream = log_stream
        self.message_prefix = message_prefix
        self.start_time = start_time
        self.status = status

    def as_dict(self):
        return {
            "ErrorMessage": self.error_message,
            "LogGroup": self.log_group,
            "LogStream": self.log_stream,
            "MessagePrefix": self.message_prefix,
            "StartTime": self.start_time,
            "Status": self.status,
        }


glue_backend = GlueBackend()
