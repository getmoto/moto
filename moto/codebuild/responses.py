import json
import re

from moto.core.responses import BaseResponse
from .models import codebuild_backends
from .exceptions import InvalidInputException
from moto.core import get_account_id


def _validate_required_params_source(source):
    try:
        assert source["type"] in ["BITBUCKET", "CODECOMMIT", "CODEPIPELINE", "GITHUB", "GITHUB_ENTERPRISE", "NO_SOURCE", "S3"]
    except AssertionError:
        raise InvalidInputException(
            "Invalid type provided: Project source type"
        )
    # if type CODECOMMIT ensure https://git-codecommit.<region>.amazonaws.com in location value
    # if type S3 ensure valid bucket name or use mock_s3
    try:
        assert source["location"]
        assert source["location"] != ""
    except (KeyError, AssertionError):
        raise InvalidInputException(
            "Project source location is required"
        )

def _validate_required_params_service_role(service_role):
    try:
        assert "arn:aws:iam::{0}:role/service-role/".format(get_account_id()) in service_role
    except AssertionError:
        raise InvalidInputException(
            "Invalid service role: Service role account ID does not match caller's account"
        )

def _validate_required_params_artifacts(artifacts):
    try:
        assert artifacts["type"] in ["CODEPIPELINE", "S3", "NO_ARTIFACTS"]
    except AssertionError:
        raise InvalidInputException(
            "Invalid type provided: Artifact type"
        )
    try:
        if artifacts["type"] == "NO_ARTIFACTS":
            try:
                assert "location" not in artifacts
            except AssertionError:
                raise InvalidInputException(
                    "Invalid artifacts: artifact type NO_ARTIFACTS should have null location"
                )
        else:
            assert artifacts["location"]
            assert artifacts["location"] != ""
    except (KeyError, AssertionError):
        raise InvalidInputException(
            "Project source location is required"
        )

def _validate_required_params_environment(environment):
    try:
        assert environment["type"] in ["WINDOWS_CONTAINER", "LINUX_CONTAINER", "LINUX_GPU_CONTAINER", "ARM_CONTAINER"]
    except AssertionError:
        raise InvalidInputException(
            "Invalid type provided: {0}".format(environment["type"])
        )
    try:
        assert environment["computeType"] in ["BUILD_GENERAL1_SMALL", "BUILD_GENERAL1_MEDIUM", "BUILD_GENERAL1_LARGE", "BUILD_GENERAL1_2XLARGE"]
    except AssertionError:
        raise InvalidInputException(
            "Invalid compute type provided: {0}".format(environment["computeType"])
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
        _validate_required_params_source(self._get_param("source"))
        _validate_required_params_service_role(self._get_param("serviceRole"))
        _validate_required_params_artifacts(self._get_param("artifacts"))
        _validate_required_params_environment(self._get_param("environment"))

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

    def list_builds(self):
        # VALIDATE PROJECT EXISTS
        # get param pulling function signatures params from .ipynb

        ids = self.codebuild_backend.list_builds()

        return json.dumps({"ids": ids})

    def delete_project(self):

        self.codebuild_backend.delete_project(
            self._get_param("name")
        )

        return

    def stop_build(self):

        metadata = self.codebuild_backend.stop_build(
            self._get_param("id")
        )

        return json.dumps({"build": metadata})