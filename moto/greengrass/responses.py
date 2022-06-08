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

        if self.method == "GET":
            return self.list_core_definitions()

        if self.method == "POST":
            return self.create_core_definition()

    def list_core_definitions(self):
        res = self.greengrass_backend.list_core_definitions()
        return (
            200,
            {"status": 200},
            json.dumps(
                {"Definitions": [core_definition.to_dict() for core_definition in res]}
            ),
        )

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

        if self.method == "PUT":
            return self.update_core_definition()

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

    def update_core_definition(self):
        core_definition_id = self.path.split("/")[-1]
        name = self._get_param("Name")
        self.greengrass_backend.update_core_definition(
            core_definition_id=core_definition_id, name=name
        )
        return 200, {"status": 200}, json.dumps({})

    def core_definition_versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.list_core_definition_versions()

        if self.method == "POST":
            return self.create_core_definition_version()

    def create_core_definition_version(self):
        core_definition_id = self.path.split("/")[-2]
        cores = self._get_param("Cores")

        res = self.greengrass_backend.create_core_definition_version(
            core_definition_id=core_definition_id, cores=cores
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def list_core_definition_versions(self):
        core_definition_id = self.path.split("/")[-2]
        res = self.greengrass_backend.list_core_definition_versions(core_definition_id)
        return (
            200,
            {"status": 200},
            json.dumps({"Versions": [core_def_ver.to_dict() for core_def_ver in res]}),
        )

    def core_definition_version(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_core_definition_version()

    def get_core_definition_version(self):
        core_definition_id = self.path.split("/")[-3]
        core_definition_version_id = self.path.split("/")[-1]
        res = self.greengrass_backend.get_core_definition_version(
            core_definition_id=core_definition_id,
            core_definition_version_id=core_definition_version_id,
        )
        return 200, {"status": 200}, json.dumps(res.to_dict(include_detail=True))

    def device_definitions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_device_definition()

    def create_device_definition(self):

        name = self._get_param("Name")
        initial_version = self._get_param("InitialVersion")
        res = self.greengrass_backend.create_device_definition(
            name=name, initial_version=initial_version
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def device_definition_versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_device_definition_version()

    def create_device_definition_version(self):

        device_definition_id = self.path.split("/")[-2]
        devices = self._get_param("Devices")

        res = self.greengrass_backend.create_device_definition_version(
            device_definition_id=device_definition_id, devices=devices
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())
