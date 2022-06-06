import json

from moto.core.responses import BaseResponse
from .models import greengrass_backends


class GreengrassResponse(BaseResponse):
    SERVICE_NAME = "greengrass"

    @property
    def greengrass_backend(self):
        return greengrass_backends[self.region]

    def core_definitions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_core_definition()

    def create_core_definition(self):
        name = self._get_param("Name")
        initial_version = self._get_param("InitialVersion")
        res = self.greengrass_backend.create_core_definition(
            name=name, initial_version=initial_version
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def core_definition(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_core_definition()

        if self.method == "DELETE":
            return self.delete_core_definition()

    def get_core_definition(self):
        core_definition_id = self.path.split("/")[-1]
        res = self.greengrass_backend.get_core_definition(
            core_definition_id=core_definition_id
        )
        return 200, {"status": 200}, json.dumps(res.to_dict())

    def delete_core_definition(self):
        core_definition_id = self.path.split("/")[-1]
        self.greengrass_backend.delete_core_definition(
            core_definition_id=core_definition_id
        )
        return 200, {"status": 200}, json.dumps({})

    def create_core_definition_version(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        core_definition_id = self.path.split("/")[-2]
        cores = self._get_param("Cores")

        res = self.greengrass_backend.create_core_definition_version(
            core_definition_id=core_definition_id, cores=cores
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())
