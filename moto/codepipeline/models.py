import json
from datetime import datetime

from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict

from moto.iam.exceptions import IAMNotFoundException

from moto.iam import iam_backends

from moto.codepipeline.exceptions import (
    InvalidStructureException,
    PipelineNotFoundException,
    ResourceNotFoundException,
    InvalidTagsException,
    TooManyTagsException,
)
from moto.core import BaseBackend, BaseModel


class CodePipeline(BaseModel):
    def __init__(self, account_id, region, pipeline):
        # the version number for a new pipeline is always 1
        pipeline["version"] = 1

        self.pipeline = self.add_default_values(pipeline)
        self.tags = {}

        self._arn = f"arn:aws:codepipeline:{region}:{account_id}:{pipeline['name']}"
        self._created = datetime.utcnow()
        self._updated = datetime.utcnow()

    @property
    def metadata(self):
        return {
            "pipelineArn": self._arn,
            "created": iso_8601_datetime_with_milliseconds(self._created),
            "updated": iso_8601_datetime_with_milliseconds(self._updated),
        }

    def add_default_values(self, pipeline):
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

    def validate_tags(self, tags):
        for tag in tags:
            if tag["key"].startswith("aws:"):
                raise InvalidTagsException(
                    "Not allowed to modify system tags. "
                    "System tags start with 'aws:'. "
                    "msg=[Caller is an end user and not allowed to mutate system tags]"
                )

        if (len(self.tags) + len(tags)) > 50:
            raise TooManyTagsException(self._arn)


class CodePipelineBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.pipelines = {}

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "codepipeline", policy_supported=False
        )

    @property
    def iam_backend(self):
        return iam_backends[self.account_id]["global"]

    def create_pipeline(self, pipeline, tags):
        name = pipeline["name"]
        if name in self.pipelines:
            raise InvalidStructureException(
                f"A pipeline with the name '{name}' already exists in account '{self.account_id}'"
            )

        try:
            role = self.iam_backend.get_role_by_arn(pipeline["roleArn"])
            trust_policy_statements = json.loads(role.assume_role_policy_document)[
                "Statement"
            ]
            trusted_service_principals = [
                i["Principal"]["Service"] for i in trust_policy_statements
            ]
            if "codepipeline.amazonaws.com" not in trusted_service_principals:
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

        self.pipelines[pipeline["name"]] = CodePipeline(
            self.account_id, self.region_name, pipeline
        )

        if tags is not None:
            self.pipelines[pipeline["name"]].validate_tags(tags)

            new_tags = {tag["key"]: tag["value"] for tag in tags}
            self.pipelines[pipeline["name"]].tags.update(new_tags)
        else:
            tags = []

        return pipeline, sorted(tags, key=lambda i: i["key"])

    def get_pipeline(self, name):
        codepipeline = self.pipelines.get(name)

        if not codepipeline:
            raise PipelineNotFoundException(
                f"Account '{self.account_id}' does not have a pipeline with name '{name}'"
            )

        return codepipeline.pipeline, codepipeline.metadata

    def update_pipeline(self, pipeline):
        codepipeline = self.pipelines.get(pipeline["name"])

        if not codepipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{pipeline['name']}'"
            )

        # version number is auto incremented
        pipeline["version"] = codepipeline.pipeline["version"] + 1
        codepipeline._updated = datetime.utcnow()
        codepipeline.pipeline = codepipeline.add_default_values(pipeline)

        return codepipeline.pipeline

    def list_pipelines(self):
        pipelines = []

        for name, codepipeline in self.pipelines.items():
            pipelines.append(
                {
                    "name": name,
                    "version": codepipeline.pipeline["version"],
                    "created": codepipeline.metadata["created"],
                    "updated": codepipeline.metadata["updated"],
                }
            )

        return sorted(pipelines, key=lambda i: i["name"])

    def delete_pipeline(self, name):
        self.pipelines.pop(name, None)

    def list_tags_for_resource(self, arn):
        name = arn.split(":")[-1]
        pipeline = self.pipelines.get(name)

        if not pipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{name}'"
            )

        tags = [{"key": key, "value": value} for key, value in pipeline.tags.items()]

        return sorted(tags, key=lambda i: i["key"])

    def tag_resource(self, arn, tags):
        name = arn.split(":")[-1]
        pipeline = self.pipelines.get(name)

        if not pipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{name}'"
            )

        pipeline.validate_tags(tags)

        for tag in tags:
            pipeline.tags.update({tag["key"]: tag["value"]})

    def untag_resource(self, arn, tag_keys):
        name = arn.split(":")[-1]
        pipeline = self.pipelines.get(name)

        if not pipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{name}'"
            )

        for key in tag_keys:
            pipeline.tags.pop(key, None)


codepipeline_backends = BackendDict(CodePipelineBackend, "codepipeline")
