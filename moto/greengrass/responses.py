import json

from moto.core.responses import BaseResponse
from .models import greengrass_backends


class GreengrassResponse(BaseResponse):
    SERVICE_NAME = "greengrass"

    @property
    def greengrass_backend(self):
        return greengrass_backends[self.region]

    def create_core_definition(self):
        name = self._get_param("Name")
        initial_version = self._get_param("InitialVersion")
        res = self.greengrass_backend.create_core_definition(
            name=name, initial_version=initial_version
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def create_core_definition_version(self):
        core_definition_id = self._get_param("CoreDefinitionId")
        cores = self._get_param("Cores")

        res = self.greengrass_backend.create_core_definition_version(
            core_definition_id=core_definition_id, cores=cores
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())
