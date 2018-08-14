from __future__ import unicode_literals

from moto.core import BaseBackend, BaseModel
from moto.compat import OrderedDict
from.exceptions import DatabaseAlreadyExistsException, TableAlreadyExistsException


class GlueBackend(BaseBackend):

    def __init__(self):
        self.databases = OrderedDict()

    def create_database(self, database_name):
        if database_name in self.databases:
            raise DatabaseAlreadyExistsException()

        database = FakeDatabase(database_name)
        self.databases[database_name] = database
        return database

    def get_database(self, database_name):
        return self.databases[database_name]

    def create_table(self, database_name, table_name, table_input):
        database = self.get_database(database_name)

        if table_name in database.tables:
            raise TableAlreadyExistsException()

        table = FakeTable(database_name, table_name, table_input)
        database.tables[table_name] = table
        return table

    def get_table(self, database_name, table_name):
        database = self.get_database(database_name)
        return database.tables[table_name]

    def get_tables(self, database_name):
        database = self.get_database(database_name)
        return [table for table_name, table in database.tables.items()]


class FakeDatabase(BaseModel):

    def __init__(self, database_name):
        self.name = database_name
        self.tables = OrderedDict()


class FakeTable(BaseModel):

    def __init__(self, database_name, table_name, table_input):
        self.database_name = database_name
        self.name = table_name
        self.table_input = table_input
        self.storage_descriptor = self.table_input.get('StorageDescriptor', {})
        self.partition_keys = self.table_input.get('PartitionKeys', [])


glue_backend = GlueBackend()
