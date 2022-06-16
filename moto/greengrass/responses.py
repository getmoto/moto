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

        if self.method == "GET":
            return self.list_device_definition()

    def create_device_definition(self):

        name = self._get_param("Name")
        initial_version = self._get_param("InitialVersion")
        res = self.greengrass_backend.create_device_definition(
            name=name, initial_version=initial_version
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def list_device_definition(self):
        res = self.greengrass_backend.list_device_definitions()
        return (
            200,
            {"status": 200},
            json.dumps(
                {
                    "Definitions": [
                        device_definition.to_dict() for device_definition in res
                    ]
                }
            ),
        )

    def device_definition_versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_device_definition_version()

        if self.method == "GET":
            return self.list_device_definition_versions()

    def create_device_definition_version(self):

        device_definition_id = self.path.split("/")[-2]
        devices = self._get_param("Devices")

        res = self.greengrass_backend.create_device_definition_version(
            device_definition_id=device_definition_id, devices=devices
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def list_device_definition_versions(self):

        device_definition_id = self.path.split("/")[-2]
        res = self.greengrass_backend.list_device_definition_versions(
            device_definition_id
        )
        return (
            200,
            {"status": 200},
            json.dumps(
                {"Versions": [device_def_ver.to_dict() for device_def_ver in res]}
            ),
        )

    def device_definition(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_device_definition()

        if self.method == "DELETE":
            return self.delete_device_definition()

        if self.method == "PUT":
            return self.update_device_definition()

    def get_device_definition(self):
        device_definition_id = self.path.split("/")[-1]
        res = self.greengrass_backend.get_device_definition(
            device_definition_id=device_definition_id
        )
        return 200, {"status": 200}, json.dumps(res.to_dict())

    def delete_device_definition(self):

        device_definition_id = self.path.split("/")[-1]
        self.greengrass_backend.delete_device_definition(
            device_definition_id=device_definition_id
        )
        return 200, {"status": 200}, json.dumps({})

    def update_device_definition(self):

        device_definition_id = self.path.split("/")[-1]
        name = self._get_param("Name")
        self.greengrass_backend.update_device_definition(
            device_definition_id=device_definition_id, name=name
        )
        return 200, {"status": 200}, json.dumps({})

    def device_definition_version(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_device_definition_version()

    def get_device_definition_version(self):
        device_definition_id = self.path.split("/")[-3]
        device_definition_version_id = self.path.split("/")[-1]
        res = self.greengrass_backend.get_device_definition_version(
            device_definition_id=device_definition_id,
            device_definition_version_id=device_definition_version_id,
        )
        return 200, {"status": 200}, json.dumps(res.to_dict(include_detail=True))

    def resource_definitions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_resource_definition()

        if self.method == "GET":
            return self.list_resource_definitions()

    def create_resource_definition(self):

        initial_version = self._get_param("InitialVersion")
        name = self._get_param("Name")
        res = self.greengrass_backend.create_resource_definition(
            name=name, initial_version=initial_version
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def list_resource_definitions(self):

        res = self.greengrass_backend.list_resource_definitions()
        return (
            200,
            {"status": 200},
            json.dumps({"Definitions": [i.to_dict() for i in res.values()]}),
        )

    def resource_definition(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_resource_definition()

        if self.method == "DELETE":
            return self.delete_resource_definition()

        if self.method == "PUT":
            return self.update_resource_definition()

    def get_resource_definition(self):
        resource_definition_id = self.path.split("/")[-1]
        res = self.greengrass_backend.get_resource_definition(
            resource_definition_id=resource_definition_id
        )
        return 200, {"status": 200}, json.dumps(res.to_dict())

    def delete_resource_definition(self):

        resource_definition_id = self.path.split("/")[-1]
        self.greengrass_backend.delete_resource_definition(
            resource_definition_id=resource_definition_id
        )
        return 200, {"status": 200}, json.dumps({})

    def update_resource_definition(self):

        resource_definition_id = self.path.split("/")[-1]
        name = self._get_param("Name")
        self.greengrass_backend.update_resource_definition(
            resource_definition_id=resource_definition_id, name=name
        )
        return 200, {"status": 200}, json.dumps({})

    def resource_definition_versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_resource_definition_version()

    def create_resource_definition_version(self):

        resource_definition_id = self.path.split("/")[-2]
        resources = self._get_param("Resources")

        res = self.greengrass_backend.create_resource_definition_version(
            resource_definition_id=resource_definition_id, resources=resources
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def function_definitions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_function_definition()

        if self.method == "GET":
            return self.list_function_definitions()

    def create_function_definition(self):

        initial_version = self._get_param("InitialVersion")
        name = self._get_param("Name")
        res = self.greengrass_backend.create_function_definition(
            name=name, initial_version=initial_version
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def list_function_definitions(self):
        res = self.greengrass_backend.list_function_definitions()
        return (
            200,
            {"status": 200},
            json.dumps(
                {"Definitions": [func_definition.to_dict() for func_definition in res]}
            ),
        )

    def function_definition(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_function_definition()

        if self.method == "DELETE":
            return self.delete_function_definition()

        if self.method == "PUT":
            return self.update_function_definition()

    def get_function_definition(self):
        function_definition_id = self.path.split("/")[-1]
        res = self.greengrass_backend.get_function_definition(
            function_definition_id=function_definition_id,
        )
        return 200, {"status": 200}, json.dumps(res.to_dict())

    def delete_function_definition(self):
        function_definition_id = self.path.split("/")[-1]
        self.greengrass_backend.delete_function_definition(
            function_definition_id=function_definition_id,
        )
        return 200, {"status": 200}, json.dumps({})

    def update_function_definition(self):
        function_definition_id = self.path.split("/")[-1]
        name = self._get_param("Name")
        self.greengrass_backend.update_function_definition(
            function_definition_id=function_definition_id, name=name
        )
        return 200, {"status": 200}, json.dumps({})

    def function_definition_versions(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "POST":
            return self.create_function_definition_version()

        if self.method == "GET":
            return self.list_function_definition_versions()

    def create_function_definition_version(self):

        default_config = self._get_param("DefaultConfig")
        function_definition_id = self.path.split("/")[-2]
        functions = self._get_param("Functions")

        res = self.greengrass_backend.create_function_definition_version(
            default_config=default_config,
            function_definition_id=function_definition_id,
            functions=functions,
        )
        return 201, {"status": 201}, json.dumps(res.to_dict())

    def list_function_definition_versions(self):
        function_definition_id = self.path.split("/")[-2]
        res = self.greengrass_backend.list_function_definition_versions(
            function_definition_id=function_definition_id
        )
        versions = [i.to_dict() for i in res.values()]
        return 200, {"status": 200}, json.dumps({"Versions": versions})

    def function_definition_version(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        if self.method == "GET":
            return self.get_function_definition_version()

    def get_function_definition_version(self):
        function_definition_id = self.path.split("/")[-3]
        function_definition_version_id = self.path.split("/")[-1]
        res = self.greengrass_backend.get_function_definition_version(
            function_definition_id=function_definition_id,
            function_definition_version_id=function_definition_version_id,
        )
        return 200, {"status": 200}, json.dumps(res.to_dict())
