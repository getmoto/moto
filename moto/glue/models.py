from __future__ import unicode_literals

from moto.core import BaseBackend, BaseModel
from moto.compat import OrderedDict
from.exceptions import DatabaseAlreadyExistsException


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


class FakeDatabase(BaseModel):

    def __init__(self, database_name):
        self.name = database_name


glue_backend = GlueBackend()
