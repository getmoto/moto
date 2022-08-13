from moto.core.responses import BaseResponse
from .models import codebuild_backends
from .exceptions import (
    InvalidInputException,
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
)
import json
import re


def _validate_required_params_source(source):
    if source["type"] not in [
        "BITBUCKET",
        "CODECOMMIT",
        "CODEPIPELINE",
        "GITHUB",
        "GITHUB_ENTERPRISE",
        "NO_SOURCE",
        "S3",
    ]:
        raise InvalidInputException("Invalid type provided: Project source type")

    if "location" not in source:
        raise InvalidInputException("Project source location is required")

    if source["location"] == "":
        raise InvalidInputException("Project source location is required")


def _validate_required_params_service_role(account_id, service_role):
    if f"arn:aws:iam::{account_id}:role/service-role/" not in service_role:
        raise InvalidInputException(
            "Invalid service role: Service role account ID does not match caller's account"
        )


def _validate_required_params_artifacts(artifacts):

    if artifacts["type"] not in ["CODEPIPELINE", "S3", "NO_ARTIFACTS"]:
        raise InvalidInputException("Invalid type provided: Artifact type")

    if artifacts["type"] == "NO_ARTIFACTS":
        if "location" in artifacts:
            raise InvalidInputException(
                "Invalid artifacts: artifact type NO_ARTIFACTS should have null location"
            )
    elif "location" not in artifacts or artifacts["location"] == "":
        raise InvalidInputException("Project source location is required")


def _validate_required_params_environment(environment):

    if environment["type"] not in [
        "WINDOWS_CONTAINER",
        "LINUX_CONTAINER",
        "LINUX_GPU_CONTAINER",
        "ARM_CONTAINER",
    ]:
        raise InvalidInputException(
            "Invalid type provided: {0}".format(environment["type"])
        )

    if environment["computeType"] not in [
        "BUILD_GENERAL1_SMALL",
        "BUILD_GENERAL1_MEDIUM",
        "BUILD_GENERAL1_LARGE",
        "BUILD_GENERAL1_2XLARGE",
    ]:
        raise InvalidInputException(
            "Invalid compute type provided: {0}".format(environment["computeType"])
        )


def _validate_required_params_project_name(name):
    if len(name) >= 150:
        raise InvalidInputException(
            "Only alphanumeric characters, dash, and underscore are supported"
        )

    if not re.match(r"^[A-Za-z]{1}.*[^!£$%^&*()+=|?`¬{}@~#:;<>\\/\[\]]$", name):
        raise InvalidInputException(
            "Only alphanumeric characters, dash, and underscore are supported"
        )


def _validate_required_params_id(build_id, build_ids):
    if ":" not in build_id:
        raise InvalidInputException("Invalid build ID provided")

    if build_id not in build_ids:
        raise ResourceNotFoundException("Build {0} does not exist".format(build_id))


class CodeBuildResponse(BaseResponse):
    @property
    def codebuild_backend(self):
        return codebuild_backends[self.current_account][self.region]

    def list_builds_for_project(self):
        _validate_required_params_project_name(self._get_param("projectName"))

        if (
            self._get_param("projectName")
            not in self.codebuild_backend.codebuild_projects.keys()
        ):
            raise ResourceNotFoundException(
                "The provided project arn:aws:codebuild:{0}:{1}:project/{2} does not exist".format(
                    self.region, self.current_account, self._get_param("projectName")
                )
            )

        ids = self.codebuild_backend.list_builds_for_project(
            self._get_param("projectName")
        )

        return json.dumps({"ids": ids})

    def create_project(self):
        _validate_required_params_source(self._get_param("source"))
        _validate_required_params_service_role(
            self.current_account, self._get_param("serviceRole")
        )
        _validate_required_params_artifacts(self._get_param("artifacts"))
        _validate_required_params_environment(self._get_param("environment"))
        _validate_required_params_project_name(self._get_param("name"))

        if self._get_param("name") in self.codebuild_backend.codebuild_projects.keys():
            raise ResourceAlreadyExistsException(
                "Project already exists: arn:aws:codebuild:{0}:{1}:project/{2}".format(
                    self.region, self.current_account, self._get_param("name")
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

        if (
            self._get_param("projectName")
            not in self.codebuild_backend.codebuild_projects.keys()
        ):
            raise ResourceNotFoundException(
                "Project cannot be found: arn:aws:codebuild:{0}:{1}:project/{2}".format(
                    self.region, self.current_account, self._get_param("projectName")
                )
            )

        metadata = self.codebuild_backend.start_build(
            self._get_param("projectName"),
            self._get_param("sourceVersion"),
            self._get_param("artifactsOverride"),
        )
        return json.dumps({"build": metadata})

    def batch_get_builds(self):
        for build_id in self._get_param("ids"):
            if ":" not in build_id:
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
        _validate_required_params_id(
            self._get_param("id"), self.codebuild_backend.list_builds()
        )

        metadata = self.codebuild_backend.stop_build(self._get_param("id"))
        return json.dumps({"build": metadata})
