import uuid
from collections import OrderedDict
from datetime import datetime

from moto.core import BaseBackend, BaseModel, get_account_id
from moto.core.utils import BackendDict, iso_8601_datetime_with_milliseconds


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

    def to_dict(self):
        return {
            "Arn": self.arn,
            "CreationTimestamp": iso_8601_datetime_with_milliseconds(
                self.created_at_datetime
            ),
            "Id": self.core_definition_id,
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


greengrass_backends = BackendDict(GreengrassBackend, "greengrass")
