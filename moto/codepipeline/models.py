import json
from datetime import datetime

from boto3 import Session
from moto.core.utils import iso_8601_datetime_with_milliseconds

from moto.iam.exceptions import IAMNotFoundException

from moto.iam import iam_backends

from moto.codepipeline.exceptions import (
    InvalidStructureException,
    PipelineNotFoundException,
)
from moto.core import BaseBackend, BaseModel

DEFAULT_ACCOUNT_ID = "123456789012"


class CodePipeline(BaseModel):
    def __init__(self, region, pipeline):
        self.pipeline = self._add_default_values(pipeline)
        self.tags = {}

        self._arn = "arn:aws:codepipeline:{0}:{1}:{2}".format(
            region, DEFAULT_ACCOUNT_ID, pipeline["name"]
        )
        self._created = datetime.utcnow()
        self._updated = datetime.utcnow()

    @property
    def metadata(self):
        return {
            "pipelineArn": self._arn,
            "created": iso_8601_datetime_with_milliseconds(self._created),
            "updated": iso_8601_datetime_with_milliseconds(self._updated),
        }

    def _add_default_values(self, pipeline):
        for stage in pipeline["stages"]:
            for action in stage["actions"]:
                if "runOrder" not in action:
                    action["runOrder"] = 1
                if "configuration" not in action:
                    action["configuration"] = {}
                if "outputArtifacts" not in action:
                    action["outputArtifacts"] = []
                if "inputArtifacts" not in action:
                    action["inputArtifacts"] = []

        return pipeline


class CodePipelineBackend(BaseBackend):
    def __init__(self):
        self.pipelines = {}

    @property
    def iam_backend(self):
        return iam_backends["global"]

    def create_pipeline(self, region, pipeline, tags):
        if pipeline["name"] in self.pipelines:
            raise InvalidStructureException(
                "A pipeline with the name '{0}' already exists in account '{1}'".format(
                    pipeline["name"], DEFAULT_ACCOUNT_ID
                )
            )

        try:
            role = self.iam_backend.get_role_by_arn(pipeline["roleArn"])
            service_principal = json.loads(role.assume_role_policy_document)[
                "Statement"
            ][0]["Principal"]["Service"]
            if "codepipeline.amazonaws.com" not in service_principal:
                raise IAMNotFoundException("")
        except IAMNotFoundException:
            raise InvalidStructureException(
                "CodePipeline is not authorized to perform AssumeRole on role {}".format(
                    pipeline["roleArn"]
                )
            )

        if len(pipeline["stages"]) < 2:
            raise InvalidStructureException(
                "Pipeline has only 1 stage(s). There should be a minimum of 2 stages in a pipeline"
            )

        self.pipelines[pipeline["name"]] = CodePipeline(region, pipeline)

        if tags:
            new_tags = {tag["key"]: tag["value"] for tag in tags}
            self.pipelines[pipeline["name"]].tags.update(new_tags)

        return pipeline, tags

    def get_pipeline(self, name):
        codepipeline = self.pipelines.get(name)

        if not codepipeline:
            raise PipelineNotFoundException(
                "Account '{0}' does not have a pipeline with name '{1}'".format(
                    DEFAULT_ACCOUNT_ID, name
                )
            )

        return codepipeline.pipeline, codepipeline.metadata


codepipeline_backends = {}
for region in Session().get_available_regions("codepipeline"):
    codepipeline_backends[region] = CodePipelineBackend()
