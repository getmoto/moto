from pydoc import source_synopsis
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from datetime import datetime
from moto.core import get_account_id
from collections import defaultdict
from random import randint
import uuid
# from .exceptions import InvalidInputException

class CodeBuildProjectMetadata(BaseModel):

    def __init__(self, project_name, source_version, artifacts, build_id, service_role):
        current_date = iso_8601_datetime_with_milliseconds(datetime.utcnow())
        self.build_metadata = dict()
        self.build_id_history = list()

        self.build_metadata_history = defaultdict(list)

        self.build_metadata["id"] = build_id
        self.build_metadata["arn"] = "arn:aws:codebuild:eu-west-2:{0}:build/{1}".format(
            get_account_id(), build_id
        )

        self.build_metadata["buildNumber"] = randint(1,100)
        self.build_metadata["startTime"] = current_date
        self.build_metadata["currentPhase"] = "QUEUED"
        self.build_metadata["buildStatus"] = "IN_PROGRESS"
        self.build_metadata["sourceVersion"] = source_version if source_version else "refs/heads/main"
        self.build_metadata["projectName"] = project_name

        self.build_metadata["phases"] = [{"phaseType": "SUBMITTED",
            "phaseStatus": "SUCCEEDED",
            "startTime": current_date,
            "endTime": current_date,
            "durationInSeconds": 0},
        {"phaseType": "QUEUED",
            "startTime": current_date}]

        self.build_metadata["source"] = {"type": "CODECOMMIT", # should be different based on what you pass in 
            "location": "https://git-codecommit.eu-west-2.amazonaws.com/v1/repos/testing",
            "gitCloneDepth": 1,
            "gitSubmodulesConfig": {"fetchSubmodules": False},
            "buildspec": "buildspec/stuff.yaml", # should present in the codebuild project somewhere
            "insecureSsl": False}

        self.build_metadata["secondarySources"] = []
        self.build_metadata["secondarySourceVersions"] = []
        self.build_metadata["artifacts"] = {"location": ""}
        self.build_metadata["secondaryArtifacts"] = []
        self.build_metadata["cache"] = {"type": "NO_CACHE"}

        self.build_metadata["environment"] = {"type": "LINUX_CONTAINER",
            "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
            "computeType": "BUILD_GENERAL1_SMALL",
            "environmentVariables": [],
            "privilegedMode": False,
            "imagePullCredentialsType": "CODEBUILD"}

        self.build_metadata["serviceRole"] = service_role
        
        self.build_metadata["logs"] = {"deepLink": "https://console.aws.amazon.com/cloudwatch/home?region=eu-west-2#logEvent:group=null;stream=null",
            "cloudWatchLogsArn": "arn:aws:logs:eu-west-2:{0}:log-group:null:log-stream:null".format(get_account_id()),
            "cloudWatchLogs": {"status": "ENABLED"},
            "s3Logs": {"status": "DISABLED", "encryptionDisabled": False}}

        self.build_metadata["timeoutInMinutes"] = 45
        self.build_metadata["queuedTimeoutInMinutes"] = 480
        self.build_metadata["buildComplete"] = False
        self.build_metadata["initiator"] = "rootme"
        self.build_metadata["encryptionKey"] = "arn:aws:kms:eu-west-2:{0}:alias/aws/s3".format(get_account_id())

class CodeBuild(BaseModel):

    def __init__(self, region, project_name, project_source=dict(), artifacts=dict(), environment=dict(), serviceRole="some_role"):
        current_date = iso_8601_datetime_with_milliseconds(datetime.utcnow())
        # remove codebuild from these names
        self.project_metadata = dict()

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
        self.project_metadata["badge"]["badgeEnabled"] = False  # this false needs to be a json false not a python false
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
        self.codebuild_projects = dict()
        self.build_history = dict()
        self.build_metadata = dict()
        self.project_name = ""

    def create_project(self, project_name, project_source, artifacts, environment, service_role):
        # if exists exit with proper response
        #project = self.codebuild_projects.get(project_name)
        # if project:
        #     raise SomeException(project_name)         # this needs to be a project name exists
        
        self.project_name = project_name
        self.service_role = service_role

        self.codebuild_projects[project_name] = CodeBuild(
            self.region_name, project_name, project_source, artifacts, environment, service_role
        )

        # empty build history
        self.build_history[project_name] = []

        return self.codebuild_projects[project_name].project_metadata

    def list_projects(self):

        projects = []
        for project,_ in self.codebuild_projects.items():
            projects.append(project)

        return projects

    def start_build(self, project_name, source_version=None, artifact_override=None):

        build_id = "{0}:{1}".format(project_name, uuid.uuid4())

        # construct a new build
        self.build_metadata[project_name] = CodeBuildProjectMetadata(
            project_name, source_version, artifact_override, build_id, self.service_role
        )

        # update build history with id
        self.build_metadata[project_name].build_id_history.append(build_id)

        # update build histroy with metadata
        self.build_metadata[project_name].build_metadata_history[project_name].append(
            self.build_metadata[project_name].build_metadata
        )

        # return current build
        return self.build_metadata[project_name].build_metadata

    def batch_get_builds(self, ids):

        metadata_by_id = []

        for project_name, metadata in self.build_metadata.items():
            for entry in metadata.build_metadata_history[project_name]:
                for id in ids:
                    if entry["id"] == id:
                        metadata_by_id.append(entry)

        return metadata_by_id


    def list_builds_for_project(self, project_name):
        # validate stuff
        try:
            return self.build_metadata[project_name].build_id_history
        except KeyError:
            return list()


    def list_builds(self):
        ids = []
        for _,history in self.build_metadata.items():
            ids.append(history.build_id_history[0])
        return ids


    def delete_project(self, project_name):

        self.build_metadata.pop(project_name, None)
        self.build_metadata.pop(project_name, None)


    def stop_build():
        pass


codebuild_backends = BackendDict(CodeBuildBackend, "codebuild")
