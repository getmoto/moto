from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from datetime import datetime
from moto.core import get_account_id
# from .exceptions import InvalidInputException


class CodeBuildProjectHistory(BaseModel):

    def __init__(self, project_name):
        self.project_build_history = list()

    def list_builds_for_project(self, project_name):
        # validate stuff
        return self.codebuild_projects[project_name].project_build_history

class CodeBuildProjectHistoryMetadata(BaseModel):

    def __init__(self, region, project_name, project_source=dict(), artifacts=dict(), environment=dict(), serviceRole="some_role"):
        current_date = iso_8601_datetime_with_milliseconds(datetime.utcnow())
        # remove codebuild from these names
        self.project_metadata = dict()
        self.project_build_history = list()


class CodeBuild(BaseModel):

    def __init__(self, region, project_name, project_source=dict(), artifacts=dict(), environment=dict(), serviceRole="some_role"):
        current_date = iso_8601_datetime_with_milliseconds(datetime.utcnow())
        # remove codebuild from these names
        self.project_metadata = dict()
        self.project_build_history = list()

        self.project_metadata["name"] = project_name
        self.project_metadata["arn"] = "arn:aws:codebuild:{0}:{1}:project/{2}".format(
            region, get_account_id(), self.project_metadata["name"]
        )
        self.project_metadata["encryptionKey"] = "arn:aws:kms:{0}:{1}:alias/aws/s3".format(
            region, get_account_id()
        )
        self.project_metadata["serviceRole"] = "arn:aws:iam::{0}:role/service-role/{1}".format(
            get_account_id(), serviceRole
        )
        self.project_metadata["lastModifiedDate"] = current_date
        self.project_metadata["created"] = current_date
        self.project_metadata["badge"] = dict()
        self.project_metadata["badge"]["badgeEnabled"] = False         # this false needs to be a json false not a python false
        self.project_metadata["environment"] = environment
        self.project_metadata["artifacts"] = artifacts
        self.project_metadata["source"] = project_source
        self.project_metadata["cache"] = dict()
        self.project_metadata["cache"]["type"] = "NO_CACHE"
        self.project_metadata["timeoutInMinutes"] = ""
        self.project_metadata["queuedTimeoutInMinutes"] = ""


class CodeBuildBackend(BaseBackend):
    """ find which functions I used in the dev branch stuff """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.codebuild_projects = {}

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "codebuild"
        )

    def create_project(self, project_name, project_source, artifacts, environment, role):
        project = self.codebuild_projects.get(project_name)
        # if project:
        #     raise SomeException(project_name)         # this needs to be a project name exists

        self.codebuild_projects[project_name] = CodeBuild(
            self.region_name, project_name, project_source, artifacts, environment, role
        )

        return self.codebuild_projects[project_name].project_metadata

    def list_projects(self):
        projects = []
        for k,v in self.codebuild_projects.items():
            projects.append(k)

        return projects

    def delete_project():
        pass

    def list_builds():
        pass

    def list_builds_for_project(self, project_name):
        # validate stuff
        return self.codebuild_projects[project_name].project_build_history


codebuild_backends = BackendDict(CodeBuildBackend, "codebuild")
