from moto.core.responses import BaseResponse
from .models import codebuild_backends
from .exceptions import (
    InvalidInputException,
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
)
from moto.core import get_account_id
import json
import re


def _validate_required_params_source(source):
    try:
        assert source["type"] in [
            "BITBUCKET",
            "CODECOMMIT",
            "CODEPIPELINE",
            "GITHUB",
            "GITHUB_ENTERPRISE",
            "NO_SOURCE",
            "S3",
        ]
    except AssertionError:
        raise InvalidInputException("Invalid type provided: Project source type")
    # if type CODECOMMIT ensure https://git-codecommit.<region>.amazonaws.com in location value
    # if type S3 ensure valid bucket name or use mock_s3
    try:
        assert source["location"]
        assert source["location"] != ""
    except (KeyError, AssertionError):
        raise InvalidInputException("Project source location is required")


def _validate_required_params_service_role(service_role):
    try:
        assert (
            "arn:aws:iam::{0}:role/service-role/".format(get_account_id())
            in service_role
        )
    except AssertionError:
        raise InvalidInputException(
            "Invalid service role: Service role account ID does not match caller's account"
        )


def _validate_required_params_artifacts(artifacts):
    try:
        assert artifacts["type"] in ["CODEPIPELINE", "S3", "NO_ARTIFACTS"]
    except AssertionError:
        raise InvalidInputException("Invalid type provided: Artifact type")
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
        raise InvalidInputException("Project source location is required")


def _validate_required_params_environment(environment):
    try:
        assert environment["type"] in [
            "WINDOWS_CONTAINER",
            "LINUX_CONTAINER",
            "LINUX_GPU_CONTAINER",
            "ARM_CONTAINER",
        ]
    except AssertionError:
        raise InvalidInputException(
            "Invalid type provided: {0}".format(environment["type"])
        )
    try:
        assert environment["computeType"] in [
            "BUILD_GENERAL1_SMALL",
            "BUILD_GENERAL1_MEDIUM",
            "BUILD_GENERAL1_LARGE",
            "BUILD_GENERAL1_2XLARGE",
        ]
    except AssertionError:
        raise InvalidInputException(
            "Invalid compute type provided: {0}".format(environment["computeType"])
        )


def _validate_required_params_project_name(name):
    try:
        # isalnum with dashes or underscores
        assert re.match(r"^[A-Za-z0-9_-]+$", name)
    except AssertionError:
        raise InvalidInputException(
            "Only alphanumeric characters, dash, and underscore are supported"
        )


class CodeBuildResponse(BaseResponse):
    @property
    def codebuild_backend(self):
        return codebuild_backends[self.region]

    def list_builds_for_project(self):
        _validate_required_params_project_name(self._get_param("projectName"))

        try:
            assert (
                self._get_param("projectName")
                in self.codebuild_backend.codebuild_projects.keys()
            )
        except AssertionError:
            raise ResourceNotFoundException(
                "The provided project arn:aws:codebuild:{0}:{1}:project/{2} does not exist".format(
                    self.region, get_account_id(), self._get_param("projectName")
                )
            )

        ids = self.codebuild_backend.list_builds_for_project(
            self._get_param("projectName")
        )

        return json.dumps({"ids": ids})

    def create_project(self):
        _validate_required_params_source(self._get_param("source"))
        _validate_required_params_service_role(self._get_param("serviceRole"))
        _validate_required_params_artifacts(self._get_param("artifacts"))
        _validate_required_params_environment(self._get_param("environment"))
        _validate_required_params_project_name(self._get_param("name"))

        try:
            assert (
                self._get_param("name")
                not in self.codebuild_backend.codebuild_projects.keys()
            )
        except AssertionError:
            raise ResourceAlreadyExistsException(
                "Project already exists: arn:aws:codebuild:{0}:{1}:project/{2}".format(
                    self.region, get_account_id(), self._get_param("name")
                )
            )

        project_metadata = self.codebuild_backend.create_project(
            self._get_param("name"),
            self._get_param("source"),
            self._get_param("artifacts"),
            self._get_param("environment"),
            self._get_param("serviceRole"),
        )

        return json.dumps({"project": project_metadata})

    def list_projects(self):
        project_metadata = self.codebuild_backend.list_projects()
        return json.dumps({"projects": project_metadata})

    def start_build(self):
        _validate_required_params_project_name(self._get_param("projectName"))

        try:
            assert (
                self._get_param("projectName")
                in self.codebuild_backend.codebuild_projects.keys()
            )
        except AssertionError:
            raise ResourceNotFoundException(
                "Project cannot be found: arn:aws:codebuild:{0}:{1}:project/{2}".format(
                    self.region, get_account_id(), self._get_param("projectName")
                )
            )

        metadata = self.codebuild_backend.start_build(
            self._get_param("projectName"),
            self._get_param("sourceVersion"),
            self._get_param("artifactsOverride"),
        )
        return json.dumps({"build": metadata})

    def batch_get_builds(self):

        try:
            for build_id in self._get_param("ids"):
                assert ":" in build_id
        except AssertionError:
            raise InvalidInputException("Invalid build ID provided")

        metadata = self.codebuild_backend.batch_get_builds(self._get_param("ids"))
        return json.dumps({"builds": metadata})

    def list_builds(self):
        ids = self.codebuild_backend.list_builds()
        return json.dumps({"ids": ids})

    def delete_project(self):
        _validate_required_params_project_name(self._get_param("name"))

        self.codebuild_backend.delete_project(self._get_param("name"))
        return

    def stop_build(self):

        try:
            assert ":" in self._get_param("id")
        except AssertionError:
            raise InvalidInputException("Invalid build ID provided")

        metadata = self.codebuild_backend.stop_build(self._get_param("id"))
        return json.dumps({"build": metadata})
