from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import glue_backend


class GlueResponse(BaseResponse):

    @property
    def glue_backend(self):
        return glue_backend

    @property
    def parameters(self):
        return json.loads(self.body)

    def create_database(self):
        database_name = self.parameters['DatabaseInput']['Name']
        self.glue_backend.create_database(database_name)
        return ""

    def get_database(self):
        database_name = self.parameters.get('Name')
        database = self.glue_backend.get_database(database_name)
        return json.dumps({'Database': {'Name': database.name}})

    def create_table(self):
        database_name = self.parameters.get('DatabaseName')
        table_input = self.parameters.get('TableInput')
        table_name = table_input.get('Name')
        self.glue_backend.create_table(database_name, table_name, table_input)
        return ""

    def get_table(self):
        database_name = self.parameters.get('DatabaseName')
        table_name = self.parameters.get('Name')
        table = self.glue_backend.get_table(database_name, table_name)
        return json.dumps({
            'Table': {
                'DatabaseName': table.database_name,
                'Name': table.name,
                'PartitionKeys': table.partition_keys,
                'StorageDescriptor': table.storage_descriptor
            }
        })

    def get_tables(self):
        database_name = self.parameters.get('DatabaseName')
        tables = self.glue_backend.get_tables(database_name)
        return json.dumps(
            {
                'TableList': [
                    {
                        'DatabaseName': table.database_name,
                        'Name': table.name,
                        'PartitionKeys': table.partition_keys,
                        'StorageDescriptor': table.storage_descriptor
                    } for table in tables
                ]
            }
        )
