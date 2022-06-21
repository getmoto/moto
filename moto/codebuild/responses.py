import json
import re

from moto.core.responses import BaseResponse
from .models import codebuild_backends
from .exceptions import InvalidInputException
from moto.core import get_account_id


def _validate_source(source):
    try:
        assert source["type"] in ["BITBUCKET", "CODECOMMIT", "CODEPIPELINE", "GITHUB", "GITHUB_ENTERPRISE", "NO_SOURCE", "S3"]
    except AssertionError:
        raise InvalidInputException(
            "Invalid type provided: Project source type"
        )


def _validate_service_role(service_role):
    print(get_account_id())
    try:
        assert "arn:aws:iam::{0}:role/service-role/".format(get_account_id()) in service_role
    except AssertionError:
        raise InvalidInputException(
            "Invalid service role: Service role account ID does not match caller's account"
        )


class CodeBuildResponse(BaseResponse):
    @property
    def codebuild_backend(self):
        return codebuild_backends[self.region]

    # call model function and stores response expects [] to be returned
    def list_builds_for_project(self):

        # if project name not valid raise custom exception for list_builds_for_project function
        # project needs to exist?

        ids = self.codebuild_backend.list_builds_for_project(
            self._get_params("project_name")
        )

        # does this just need to run ids, or should it be build here? probably built here?
        return json.dumps({"ids": ids})

    def create_project(self):
        _validate_source(self._get_param("source"))
        _validate_service_role(self._get_param("serviceRole"))

        codebuild_project_metadata = self.codebuild_backend.create_project(
            self._get_param("name"), self._get_param("source"), self._get_param("artifacts"), self._get_param("environment"), self._get_param("serviceRole")
        )

        return json.dumps({"project": codebuild_project_metadata})

    def list_projects(self):
        codebuild_project_metadata = self.codebuild_backend.list_projects()
        return json.dumps({"projects": codebuild_project_metadata})
