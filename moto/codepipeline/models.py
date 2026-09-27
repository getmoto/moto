import json
from typing import Any

from moto.codepipeline.exceptions import (
    InvalidStructureException,
    InvalidTagsException,
    PipelineExecutionNotFoundException,
    PipelineNotFoundException,
    ResourceNotFoundException,
    TooManyTagsException,
)
from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, utcnow
from moto.iam.exceptions import NotFoundException as IAMNotFoundException
from moto.iam.models import IAMBackend, iam_backends
from moto.moto_api._internal import mock_random
from moto.utilities.utils import get_partition


class PipelineExecution(BaseModel):
    def __init__(
        self,
        pipeline_name: str,
        pipeline_version: int,
        variables: list[dict[str, str]] | None,
    ):
        self.pipeline_execution_id = str(mock_random.uuid4())
        self.pipeline_name = pipeline_name
        self.pipeline_version = pipeline_version
        self.variables = variables or []
        self.start_time = utcnow()
        self.last_update_time = self.start_time
        # moto doesn't actually run any actions, so the execution is
        # considered to have succeeded as soon as it's started
        self.status = "Succeeded"
        self.status_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipelineName": self.pipeline_name,
            "pipelineVersion": self.pipeline_version,
            "pipelineExecutionId": self.pipeline_execution_id,
            "status": self.status,
            "statusSummary": self.status_summary,
            "artifactRevisions": [],
            # response shape is ResolvedPipelineVariable (name/resolvedValue),
            # not PipelineVariable (name/value) used on the request side
            "variables": [
                {"name": v["name"], "resolvedValue": v["value"]} for v in self.variables
            ],
            "trigger": {
                "triggerType": "StartPipelineExecution",
                "triggerDetail": "",
            },
        }

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "pipelineExecutionId": self.pipeline_execution_id,
            "status": self.status,
            "statusSummary": self.status_summary,
            "startTime": iso_8601_datetime_with_milliseconds(self.start_time),
            "lastUpdateTime": iso_8601_datetime_with_milliseconds(
                self.last_update_time
            ),
            "sourceRevisions": [],
            "trigger": {
                "triggerType": "StartPipelineExecution",
                "triggerDetail": "",
            },
        }


class CodePipeline(BaseModel):
    def __init__(self, account_id: str, region: str, pipeline: dict[str, Any]):
        # the version number for a new pipeline is always 1
        pipeline["version"] = 1

        self.pipeline = self.add_default_values(pipeline)
        self.tags: dict[str, str] = {}
        # keyed by pipelineExecutionId, insertion order == chronological order
        self.executions: dict[str, PipelineExecution] = {}

        self._arn = f"arn:{get_partition(region)}:codepipeline:{region}:{account_id}:{pipeline['name']}"
        self._created = utcnow()
        self._updated = utcnow()

    @property
    def metadata(self) -> dict[str, str]:
        return {
            "pipelineArn": self._arn,
            "created": iso_8601_datetime_with_milliseconds(self._created),
            "updated": iso_8601_datetime_with_milliseconds(self._updated),
        }

    def add_default_values(self, pipeline: dict[str, Any]) -> dict[str, Any]:
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

    def validate_tags(self, tags: list[dict[str, str]]) -> None:
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
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.pipelines: dict[str, CodePipeline] = {}

    @staticmethod
    def default_vpc_endpoint_service(
        service_region: str, zones: list[str]
    ) -> list[dict[str, str]]:
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "codepipeline", policy_supported=False
        )

    @property
    def iam_backend(self) -> IAMBackend:
        return iam_backends[self.account_id][self.partition]

    def create_pipeline(
        self, pipeline: dict[str, Any], tags: list[dict[str, str]]
    ) -> tuple[dict[str, Any], list[dict[str, str]]]:
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
                f"CodePipeline is not authorized to perform AssumeRole on role {pipeline['roleArn']}"
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

    def get_pipeline(self, name: str) -> tuple[dict[str, Any], dict[str, str]]:
        codepipeline = self.pipelines.get(name)

        if not codepipeline:
            raise PipelineNotFoundException(
                f"Account '{self.account_id}' does not have a pipeline with name '{name}'"
            )

        return codepipeline.pipeline, codepipeline.metadata

    def start_pipeline_execution(
        self, name: str, variables: list[dict[str, str]] | None
    ) -> str:
        codepipeline = self.pipelines.get(name)

        if not codepipeline:
            raise PipelineNotFoundException(
                f"Account '{self.account_id}' does not have a pipeline with name '{name}'"
            )

        execution = PipelineExecution(
            pipeline_name=name,
            pipeline_version=codepipeline.pipeline["version"],
            variables=variables,
        )
        codepipeline.executions[execution.pipeline_execution_id] = execution

        return execution.pipeline_execution_id

    def get_pipeline_execution(
        self, pipeline_name: str, pipeline_execution_id: str
    ) -> PipelineExecution:
        codepipeline = self.pipelines.get(pipeline_name)

        if not codepipeline:
            raise PipelineNotFoundException(
                f"Account '{self.account_id}' does not have a pipeline with name '{pipeline_name}'"
            )

        execution = codepipeline.executions.get(pipeline_execution_id)
        if not execution:
            raise PipelineExecutionNotFoundException(
                f"Account '{self.account_id}' does not have an execution with id "
                f"'{pipeline_execution_id}' for pipeline '{pipeline_name}'"
            )

        return execution

    def list_pipeline_executions(
        self, pipeline_name: str, max_results: int | None
    ) -> list[dict[str, Any]]:
        codepipeline = self.pipelines.get(pipeline_name)

        if not codepipeline:
            raise PipelineNotFoundException(
                f"Account '{self.account_id}' does not have a pipeline with name '{pipeline_name}'"
            )

        # most recent execution first
        executions = list(reversed(codepipeline.executions.values()))
        if max_results:
            executions = executions[:max_results]

        return [execution.to_summary_dict() for execution in executions]

    def update_pipeline(self, pipeline: dict[str, Any]) -> dict[str, Any]:
        codepipeline = self.pipelines.get(pipeline["name"])

        if not codepipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{pipeline['name']}'"
            )

        # version number is auto incremented
        pipeline["version"] = codepipeline.pipeline["version"] + 1
        codepipeline._updated = utcnow()
        codepipeline.pipeline = codepipeline.add_default_values(pipeline)

        return codepipeline.pipeline

    def list_pipelines(self) -> list[dict[str, str]]:
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

    def delete_pipeline(self, name: str) -> None:
        self.pipelines.pop(name, None)

    def list_tags_for_resource(self, arn: str) -> list[dict[str, str]]:
        name = arn.split(":")[-1]
        pipeline = self.pipelines.get(name)

        if not pipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{name}'"
            )

        tags = [{"key": key, "value": value} for key, value in pipeline.tags.items()]

        return sorted(tags, key=lambda i: i["key"])

    def tag_resource(self, arn: str, tags: list[dict[str, str]]) -> None:
        name = arn.split(":")[-1]
        pipeline = self.pipelines.get(name)

        if not pipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{name}'"
            )

        pipeline.validate_tags(tags)

        for tag in tags:
            pipeline.tags.update({tag["key"]: tag["value"]})

    def untag_resource(self, arn: str, tag_keys: list[str]) -> None:
        name = arn.split(":")[-1]
        pipeline = self.pipelines.get(name)

        if not pipeline:
            raise ResourceNotFoundException(
                f"The account with id '{self.account_id}' does not include a pipeline with the name '{name}'"
            )

        for key in tag_keys:
            pipeline.tags.pop(key, None)


codepipeline_backends = BackendDict(CodePipelineBackend, "codepipeline")
