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


    def list_builds_for_project(self):
        # VALIDATE PROJECT EXISTS
        # get param pulling function signatures params from .ipynb

        ids = self.codebuild_backend.list_builds_for_project(
            self._get_param("projectName")
        )

        return json.dumps({"ids": ids})


    def create_project(self):
        _validate_source(self._get_param("source"))
        _validate_service_role(self._get_param("serviceRole"))

        project_metadata = self.codebuild_backend.create_project(
            self._get_param("name"), self._get_param("source"), self._get_param("artifacts"), self._get_param("environment"), self._get_param("serviceRole")
        )

        return json.dumps({"project": project_metadata})


    def list_projects(self):
        project_metadata = self.codebuild_backend.list_projects()
        return json.dumps({"projects": project_metadata})


    def start_build(self):
  
        metadata = self.codebuild_backend.start_build(
            self._get_param("projectName"), self._get_param("sourceVersion"), self._get_param("artifactsOverride")
        )

        return json.dumps({"build": metadata})

    def batch_get_builds(self):

        metadata = self.codebuild_backend.batch_get_builds(
            self._get_param("ids")
        )

        return json.dumps({"builds": metadata})