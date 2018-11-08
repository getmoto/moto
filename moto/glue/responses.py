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

        return json.dumps({'Table': table.as_dict()})

    def update_table(self):
        database_name = self.parameters.get('DatabaseName')
        table_input = self.parameters.get('TableInput')
        table_name = table_input.get('Name')
        table = self.glue_backend.get_table(database_name, table_name)
        table.update(table_input)
        return ""

    def get_table_versions(self):
        database_name = self.parameters.get('DatabaseName')
        table_name = self.parameters.get('TableName')
        table = self.glue_backend.get_table(database_name, table_name)

        return json.dumps({
            "TableVersions": [
                {
                    "Table": table.as_dict(version=n),
                    "VersionId": str(n + 1),
                } for n in range(len(table.versions))
            ],
        })

    def get_table_version(self):
        database_name = self.parameters.get('DatabaseName')
        table_name = self.parameters.get('TableName')
        table = self.glue_backend.get_table(database_name, table_name)
        ver_id = self.parameters.get('VersionId')

        return json.dumps({
            "TableVersion": {
                "Table": table.as_dict(version=ver_id),
                "VersionId": ver_id,
            },
        })

    def get_tables(self):
        database_name = self.parameters.get('DatabaseName')
        tables = self.glue_backend.get_tables(database_name)
        return json.dumps({
            'TableList': [
                table.as_dict() for table in tables
            ]
        })

    def get_partitions(self):
        database_name = self.parameters.get('DatabaseName')
        table_name = self.parameters.get('TableName')
        if 'Expression' in self.parameters:
            raise NotImplementedError("Expression filtering in get_partitions is not implemented in moto")
        table = self.glue_backend.get_table(database_name, table_name)

        return json.dumps({
            'Partitions': [
                p.as_dict() for p in table.get_partitions()
            ]
        })

    def get_partition(self):
        database_name = self.parameters.get('DatabaseName')
        table_name = self.parameters.get('TableName')
        values = self.parameters.get('PartitionValues')

        table = self.glue_backend.get_table(database_name, table_name)

        p = table.get_partition(values)

        return json.dumps({'Partition': p.as_dict()})

    def create_partition(self):
        database_name = self.parameters.get('DatabaseName')
        table_name = self.parameters.get('TableName')
        part_input = self.parameters.get('PartitionInput')

        table = self.glue_backend.get_table(database_name, table_name)
        table.create_partition(part_input)

        return ""

    def update_partition(self):
        database_name = self.parameters.get('DatabaseName')
        table_name = self.parameters.get('TableName')
        part_input = self.parameters.get('PartitionInput')
        part_to_update = self.parameters.get('PartitionValueList')

        table = self.glue_backend.get_table(database_name, table_name)
        table.update_partition(part_to_update, part_input)

        return ""
