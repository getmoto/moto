from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from datetime import datetime
from moto.core import get_account_id
# from .exceptions import InvalidInputException


class CodeBuild(BaseModel):

    def __init__(self, region, project_name, project_source=dict(), artifacts=dict(), environment=dict(), serviceRole="some_role"):
        current_date = iso_8601_datetime_with_milliseconds(datetime.utcnow())
        self.codebuild_project_metadata = dict()

        self.codebuild_project_metadata["name"] = project_name
        self.codebuild_project_metadata["arn"] = "arn:aws:codebuild:{0}:{1}:project/{2}".format(
            region, get_account_id(), self.codebuild_project_metadata["name"]
        )
        self.codebuild_project_metadata["encryptionKey"] = "arn:aws:kms:{0}:{1}:alias/aws/s3".format(
            region, get_account_id()
        )
        self.codebuild_project_metadata["serviceRole"] = "arn:aws:iam::{0}:role/service-role/{1}".format(
            get_account_id(), serviceRole
        )
        self.codebuild_project_metadata["lastModifiedDate"] = current_date
        self.codebuild_project_metadata["created"] = current_date
        self.codebuild_project_metadata["badge"] = dict()
        self.codebuild_project_metadata["badge"]["badgeEnabled"] = False         # this false needs to be a json false not a python false
        self.codebuild_project_metadata["environment"] = environment
        self.codebuild_project_metadata["artifacts"] = artifacts
        self.codebuild_project_metadata["source"] = project_source
        self.codebuild_project_metadata["cache"] = dict()
        self.codebuild_project_metadata["cache"]["type"] = "NO_CACHE"
        self.codebuild_project_metadata["timeoutInMinutes"] = ""
        self.codebuild_project_metadata["queuedTimeoutInMinutes"] = ""


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

        return self.codebuild_projects[project_name].codebuild_project_metadata

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
        # validate some stuff
        self.code_build_projects[project_name] = CodeBuild(project_name)
        # return the ids ; there must be a codebuild project and there must be a history to return anyything but []
        # create the code build project first
        return self.code_build_projects[project_name].ids


codebuild_backends = BackendDict(CodeBuildBackend, "codebuild")
