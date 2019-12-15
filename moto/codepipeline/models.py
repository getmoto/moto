import json

from boto3 import Session
from moto.iam.exceptions import IAMNotFoundException

from moto.iam import iam_backends

from moto.codepipeline.exceptions import InvalidStructureException
from moto.core import BaseBackend, BaseModel

DEFAULT_ACCOUNT_ID = "123456789012"


class CodePipeline(BaseModel):
    def __init__(self, pipeline):
        self.pipeline = self._add_default_values(pipeline)
        self.tags = {}

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


class CodePipelineBackend(BaseBackend):
    def __init__(self):
        self.pipelines = {}

    @property
    def iam_backend(self):
        return iam_backends["global"]

    def create_pipeline(self, pipeline, tags):
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

        self.pipelines[pipeline["name"]] = CodePipeline(pipeline)

        if tags:
            new_tags = {tag["key"]: tag["value"] for tag in tags}
            self.pipelines[pipeline["name"]].tags.update(new_tags)

        return pipeline, tags


codepipeline_backends = {}
for region in Session().get_available_regions("codepipeline"):
    codepipeline_backends[region] = CodePipelineBackend()
