import uuid
from collections import OrderedDict
from datetime import datetime

from moto.core import BaseBackend, BaseModel, get_account_id
from moto.core.utils import BackendDict, iso_8601_datetime_with_milliseconds
from .exceptions import (
    IdNotFoundException,
    InvalidContainerDefinitionException,
    VersionNotFoundException,
)


class FakeCoreDefinition(BaseModel):
    def __init__(self, region_name, name):
        self.region_name = region_name
        self.name = name
        self.id = str(uuid.uuid4())
        self.arn = f"arn:aws:greengrass:{region_name}:{get_account_id()}:greengrass/definition/cores/{self.id}"
        self.created_at_datetime = datetime.utcnow()
        self.latest_version = ""
        self.latest_version_arn = ""

    def to_dict(self):
        return {
            "Arn": self.arn,
            "CreationTimestamp": iso_8601_datetime_with_milliseconds(
                self.created_at_datetime
            ),
            "Id": self.id,
            "LastUpdatedTimestamp": iso_8601_datetime_with_milliseconds(
                self.created_at_datetime
            ),
            "LatestVersion": self.latest_version,
            "LatestVersionArn": self.latest_version_arn,
            "Name": self.name,
        }


class FakeCoreDefinitionVersion(BaseModel):
    def __init__(self, region_name, core_definition_id, definition):
        self.region_name = region_name
        self.core_definition_id = core_definition_id
        self.definition = definition
        self.version = str(uuid.uuid4())
        self.arn = f"arn:aws:greengrass:{region_name}:{get_account_id()}:greengrass/definition/cores/{self.core_definition_id}/versions/{self.version}"
        self.created_at_datetime = datetime.utcnow()

    def to_dict(self, include_detail=False):
        obj = {
            "Arn": self.arn,
            "CreationTimestamp": iso_8601_datetime_with_milliseconds(
                self.created_at_datetime
            ),
            "Id": self.core_definition_id,
            "Version": self.version,
        }

        if include_detail:
            obj["Definition"] = self.definition

        return obj


class FakeDeviceDefinition(BaseModel):
    def __init__(self, region_name, name, initial_version):
        self.region_name = region_name
        self.id = str(uuid.uuid4())
        self.arn = f"arn:aws:greengrass:{region_name}:{get_account_id()}:greengrass/definition/devices/{self.id}"
        self.created_at_datetime = datetime.utcnow()
        self.update_at_datetime = datetime.utcnow()
        self.latest_version = ""
        self.latest_version_arn = ""
        self.name = name
        self.initial_version = initial_version

    def to_dict(self):
        res = {
            "Arn": self.arn,
            "CreationTimestamp": iso_8601_datetime_with_milliseconds(
                self.created_at_datetime
            ),
            "Id": self.id,
            "LastUpdatedTimestamp": iso_8601_datetime_with_milliseconds(
                self.update_at_datetime
            ),
            "LatestVersion": self.latest_version,
            "LatestVersionArn": self.latest_version_arn,
        }
        if self.name is not None:
            res["Name"] = self.name
        return res


class FakeDeviceDefinitionVersion(BaseModel):
    def __init__(self, region_name, device_definition_id, devices):
        self.region_name = region_name
        self.device_definition_id = device_definition_id
        self.devices = devices
        self.version = str(uuid.uuid4())
        self.arn = f"arn:aws:greengrass:{region_name}:{get_account_id()}:/greengrass/definition/devices/{self.device_definition_id}/versions/{self.version}"
        self.created_at_datetime = datetime.utcnow()

    def to_dict(self):
        return {
            "Arn": self.arn,
            "CreationTimestamp": iso_8601_datetime_with_milliseconds(
                self.created_at_datetime
            ),
            "Definition": {"Devices": self.devices},
            "Id": self.device_definition_id,
            "Version": self.version,
        }


class GreengrassBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.groups = OrderedDict()
        self.group_versions = OrderedDict()
        self.core_definitions = OrderedDict()
        self.core_definition_versions = OrderedDict()
        self.device_definitions = OrderedDict()
        self.device_definition_versions = OrderedDict()
        self.function_definitions = OrderedDict()
        self.function_definition_versions = OrderedDict()
        self.resource_definitions = OrderedDict()
        self.resource_definition_versions = OrderedDict()
        self.subscription_definitions = OrderedDict()
        self.subscription_definition_versions = OrderedDict()
        self.deployments = OrderedDict()

    def create_core_definition(self, name, initial_version):

        core_definition = FakeCoreDefinition(self.region_name, name)
        self.core_definitions[core_definition.id] = core_definition
        self.create_core_definition_version(
            core_definition.id, initial_version["Cores"]
        )
        return core_definition

    def list_core_definitions(self):
        return self.core_definitions.values()

    def get_core_definition(self, core_definition_id):

        if core_definition_id not in self.core_definitions:
            raise IdNotFoundException("That Core List Definition does not exist")
        return self.core_definitions[core_definition_id]

    def delete_core_definition(self, core_definition_id):
        if core_definition_id not in self.core_definitions:
            raise IdNotFoundException("That cores definition does not exist.")
        del self.core_definitions[core_definition_id]
        del self.core_definition_versions[core_definition_id]

    def update_core_definition(self, core_definition_id, name):

        if name == "":
            raise InvalidContainerDefinitionException(
                "Input does not contain any attributes to be updated"
            )
        if core_definition_id not in self.core_definitions:
            raise IdNotFoundException("That cores definition does not exist.")
        self.core_definitions[core_definition_id].name = name

    def create_core_definition_version(self, core_definition_id, cores):

        definition = {"Cores": cores}
        core_def_ver = FakeCoreDefinitionVersion(
            self.region_name, core_definition_id, definition
        )
        core_def_vers = self.core_definition_versions.get(
            core_def_ver.core_definition_id, {}
        )
        core_def_vers[core_def_ver.version] = core_def_ver
        self.core_definition_versions[core_def_ver.core_definition_id] = core_def_vers

        self.core_definitions[core_definition_id].latest_version = core_def_ver.version
        self.core_definitions[core_definition_id].latest_version_arn = core_def_ver.arn

        return core_def_ver

    def list_core_definition_versions(self, core_definition_id):

        if core_definition_id not in self.core_definitions:
            raise IdNotFoundException("That cores definition does not exist.")
        return self.core_definition_versions[core_definition_id].values()

    def get_core_definition_version(
        self, core_definition_id, core_definition_version_id
    ):

        if core_definition_id not in self.core_definitions:
            raise IdNotFoundException("That cores definition does not exist.")

        if (
            core_definition_version_id
            not in self.core_definition_versions[core_definition_id]
        ):
            raise VersionNotFoundException(
                f"Version {core_definition_version_id} of Core List Definition {core_definition_id} does not exist."
            )

        return self.core_definition_versions[core_definition_id][
            core_definition_version_id
        ]

    def create_device_definition(self, name, initial_version):
        device_def = FakeDeviceDefinition(self.region_name, name, initial_version)
        self.device_definitions[device_def.id] = device_def
        init_ver = device_def.initial_version
        init_device_def = init_ver.get("Devices", {})
        self.create_device_definition_version(device_def.id, init_device_def)

        return device_def

    def create_device_definition_version(self, device_definition_id, devices):

        if device_definition_id not in self.device_definitions:
            raise IdNotFoundException("That devices definition does not exist.")

        device_ver = FakeDeviceDefinitionVersion(
            self.region_name, device_definition_id, devices
        )
        device_vers = self.device_definition_versions.get(
            device_ver.device_definition_id, {}
        )
        device_vers[device_ver.version] = device_ver
        self.device_definition_versions[device_ver.device_definition_id] = device_vers
        self.device_definitions[
            device_definition_id
        ].latest_version = device_ver.version
        self.device_definitions[
            device_definition_id
        ].latest_version_arn = device_ver.arn

        return device_ver


greengrass_backends = BackendDict(GreengrassBackend, "greengrass")
