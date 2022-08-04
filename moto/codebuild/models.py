from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from collections import defaultdict
from random import randint
from dateutil import parser
import datetime
import uuid


class CodeBuildProjectMetadata(BaseModel):
    def __init__(
        self,
        account_id,
        region_name,
        project_name,
        source_version,
        artifacts,
        build_id,
        service_role,
    ):
        current_date = iso_8601_datetime_with_milliseconds(datetime.datetime.utcnow())
        self.build_metadata = dict()

        self.build_metadata["id"] = build_id
        self.build_metadata[
            "arn"
        ] = f"arn:aws:codebuild:{region_name}:{account_id}:build/{build_id}"

        self.build_metadata["buildNumber"] = randint(1, 100)
        self.build_metadata["startTime"] = current_date
        self.build_metadata["currentPhase"] = "QUEUED"
        self.build_metadata["buildStatus"] = "IN_PROGRESS"
        self.build_metadata["sourceVersion"] = (
            source_version if source_version else "refs/heads/main"
        )
        self.build_metadata["projectName"] = project_name

        self.build_metadata["phases"] = [
            {
                "phaseType": "SUBMITTED",
                "phaseStatus": "SUCCEEDED",
                "startTime": current_date,
                "endTime": current_date,
                "durationInSeconds": 0,
            },
            {"phaseType": "QUEUED", "startTime": current_date},
        ]

        self.build_metadata["source"] = {
            "type": "CODECOMMIT",  # should be different based on what you pass in
            "location": "https://git-codecommit.eu-west-2.amazonaws.com/v1/repos/testing",
            "gitCloneDepth": 1,
            "gitSubmodulesConfig": {"fetchSubmodules": False},
            "buildspec": "buildspec/stuff.yaml",  # should present in the codebuild project somewhere
            "insecureSsl": False,
        }

        self.build_metadata["secondarySources"] = []
        self.build_metadata["secondarySourceVersions"] = []
        self.build_metadata["artifacts"] = artifacts
        self.build_metadata["secondaryArtifacts"] = []
        self.build_metadata["cache"] = {"type": "NO_CACHE"}

        self.build_metadata["environment"] = {
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
            "computeType": "BUILD_GENERAL1_SMALL",
            "environmentVariables": [],
            "privilegedMode": False,
            "imagePullCredentialsType": "CODEBUILD",
        }

        self.build_metadata["serviceRole"] = service_role

        self.build_metadata["logs"] = {
            "deepLink": "https://console.aws.amazon.com/cloudwatch/home?region=eu-west-2#logEvent:group=null;stream=null",
            "cloudWatchLogsArn": f"arn:aws:logs:{region_name}:{account_id}:log-group:null:log-stream:null",
            "cloudWatchLogs": {"status": "ENABLED"},
            "s3Logs": {"status": "DISABLED", "encryptionDisabled": False},
        }

        self.build_metadata["timeoutInMinutes"] = 45
        self.build_metadata["queuedTimeoutInMinutes"] = 480
        self.build_metadata["buildComplete"] = False
        self.build_metadata["initiator"] = "rootme"
        self.build_metadata[
            "encryptionKey"
        ] = f"arn:aws:kms:{region_name}:{account_id}:alias/aws/s3"


class CodeBuild(BaseModel):
    def __init__(
        self,
        account_id,
        region,
        project_name,
        project_source,
        artifacts,
        environment,
        serviceRole="some_role",
    ):
        current_date = iso_8601_datetime_with_milliseconds(datetime.datetime.utcnow())
        self.project_metadata = dict()

        self.project_metadata["name"] = project_name
        self.project_metadata["arn"] = "arn:aws:codebuild:{0}:{1}:project/{2}".format(
            region, account_id, self.project_metadata["name"]
        )
        self.project_metadata[
            "encryptionKey"
        ] = f"arn:aws:kms:{region}:{account_id}:alias/aws/s3"
        self.project_metadata[
            "serviceRole"
        ] = f"arn:aws:iam::{account_id}:role/service-role/{serviceRole}"
        self.project_metadata["lastModifiedDate"] = current_date
        self.project_metadata["created"] = current_date
        self.project_metadata["badge"] = dict()
        self.project_metadata["badge"][
            "badgeEnabled"
        ] = False  # this false needs to be a json false not a python false
        self.project_metadata["environment"] = environment
        self.project_metadata["artifacts"] = artifacts
        self.project_metadata["source"] = project_source
        self.project_metadata["cache"] = dict()
        self.project_metadata["cache"]["type"] = "NO_CACHE"
        self.project_metadata["timeoutInMinutes"] = ""
        self.project_metadata["queuedTimeoutInMinutes"] = ""


class CodeBuildBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.codebuild_projects = dict()
        self.build_history = dict()
        self.build_metadata = dict()
        self.build_metadata_history = defaultdict(list)

    def create_project(
        self, project_name, project_source, artifacts, environment, service_role
    ):
        # required in other functions that don't
        self.project_name = project_name
        self.service_role = service_role

        self.codebuild_projects[project_name] = CodeBuild(
            self.account_id,
            self.region_name,
            project_name,
            project_source,
            artifacts,
            environment,
            service_role,
        )

        # empty build history
        self.build_history[project_name] = list()

        return self.codebuild_projects[project_name].project_metadata

    def list_projects(self):

        projects = []

        for project in self.codebuild_projects.keys():
            projects.append(project)

        return projects

    def start_build(self, project_name, source_version=None, artifact_override=None):

        build_id = "{0}:{1}".format(project_name, uuid.uuid4())

        # construct a new build
        self.build_metadata[project_name] = CodeBuildProjectMetadata(
            self.account_id,
            self.region_name,
            project_name,
            source_version,
            artifact_override,
            build_id,
            self.service_role,
        )

        self.build_history[project_name].append(build_id)

        # update build histroy with metadata for build id
        self.build_metadata_history[project_name].append(
            self.build_metadata[project_name].build_metadata
        )

        return self.build_metadata[project_name].build_metadata

    def _set_phases(self, phases):
        current_date = iso_8601_datetime_with_milliseconds(datetime.datetime.utcnow())
        # No phaseStatus for QUEUED on first start
        for existing_phase in phases:
            if existing_phase["phaseType"] == "QUEUED":
                existing_phase["phaseStatus"] = "SUCCEEDED"

        statuses = [
            "PROVISIONING",
            "DOWNLOAD_SOURCE",
            "INSTALL",
            "PRE_BUILD",
            "BUILD",
            "POST_BUILD",
            "UPLOAD_ARTIFACTS",
            "FINALIZING",
            "COMPLETED",
        ]

        for status in statuses:
            phase = dict()
            phase["phaseType"] = status
            phase["phaseStatus"] = "SUCCEEDED"
            phase["startTime"] = current_date
            phase["endTime"] = current_date
            phase["durationInSeconds"] = randint(10, 100)
            phases.append(phase)

        return phases

    def batch_get_builds(self, ids):
        batch_build_metadata = []

        for metadata in self.build_metadata_history.values():
            for build in metadata:
                if build["id"] in ids:
                    build["phases"] = self._set_phases(build["phases"])
                    build["endTime"] = iso_8601_datetime_with_milliseconds(
                        parser.parse(build["startTime"])
                        + datetime.timedelta(minutes=randint(1, 5))
                    )
                    build["currentPhase"] = "COMPLETED"
                    build["buildStatus"] = "SUCCEEDED"

                    batch_build_metadata.append(build)

        return batch_build_metadata

    def list_builds_for_project(self, project_name):
        try:
            return self.build_history[project_name]
        except KeyError:
            return list()

    def list_builds(self):
        ids = []

        for build_ids in self.build_history.values():
            ids += build_ids
        return ids

    def delete_project(self, project_name):
        self.build_metadata.pop(project_name, None)
        self.codebuild_projects.pop(project_name, None)

    def stop_build(self, build_id):

        for metadata in self.build_metadata_history.values():
            for build in metadata:
                if build["id"] == build_id:
                    # set completion properties with variable completion time
                    build["phases"] = self._set_phases(build["phases"])
                    build["endTime"] = iso_8601_datetime_with_milliseconds(
                        parser.parse(build["startTime"])
                        + datetime.timedelta(minutes=randint(1, 5))
                    )
                    build["currentPhase"] = "COMPLETED"
                    build["buildStatus"] = "STOPPED"

                    return build


codebuild_backends = BackendDict(CodeBuildBackend, "codebuild")
