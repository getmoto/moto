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
