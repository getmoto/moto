from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import CodePipelineBackend, codepipeline_backends


class CodePipelineResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="codepipeline")
        self.automated_parameter_parsing = True

    @property
    def codepipeline_backend(self) -> CodePipelineBackend:
        return codepipeline_backends[self.current_account][self.region]

    def create_pipeline(self) -> ActionResult:
        pipeline, tags = self.codepipeline_backend.create_pipeline(
            self._get_param("pipeline"), self._get_param("tags")
        )

        return ActionResult({"pipeline": pipeline, "tags": tags})

    def get_pipeline(self) -> ActionResult:
        codepipeline = self.codepipeline_backend.get_pipeline(self._get_param("name"))
        result = {
            "pipeline": codepipeline.pipeline,
            "metadata": {
                "pipelineArn": codepipeline.arn,
                "created": codepipeline.created,
                "updated": codepipeline.updated,
            },
        }
        return ActionResult(result)

    def start_pipeline_execution(self) -> ActionResult:
        pipeline_execution_id = self.codepipeline_backend.start_pipeline_execution(
            self._get_param("name"), self._get_param("variables")
        )

        return ActionResult({"pipelineExecutionId": pipeline_execution_id})

    def get_pipeline_execution(self) -> ActionResult:
        execution = self.codepipeline_backend.get_pipeline_execution(
            self._get_param("pipelineName"), self._get_param("pipelineExecutionId")
        )
        result = {
            "pipelineExecution": {
                "pipelineName": execution.pipeline_name,
                "pipelineVersion": execution.pipeline_version,
                "pipelineExecutionId": execution.pipeline_execution_id,
                "status": execution.status,
                "statusSummary": execution.status_summary,
                "artifactRevisions": [],
                # response shape is ResolvedPipelineVariable (name/resolvedValue),
                # not PipelineVariable (name/value) used on the request side
                "variables": [
                    {"name": v["name"], "resolvedValue": v["value"]}
                    for v in execution.variables
                ],
                "trigger": {
                    "triggerType": "StartPipelineExecution",
                    "triggerDetail": "",
                },
            }
        }
        return ActionResult(result)

    def list_pipeline_executions(self) -> ActionResult:
        executions = self.codepipeline_backend.list_pipeline_executions(
            self._get_param("pipelineName"), self._get_param("maxResults")
        )
        result: dict[str, Any] = {
            "pipelineExecutionSummaries": [
                {
                    "pipelineExecutionId": execution.pipeline_execution_id,
                    "status": execution.status,
                    "statusSummary": execution.status_summary,
                    "startTime": execution.start_time,
                    "lastUpdateTime": execution.last_update_time,
                    "sourceRevisions": [],
                    "trigger": {
                        "triggerType": "StartPipelineExecution",
                        "triggerDetail": "",
                    },
                }
                for execution in executions
            ],
        }
        return ActionResult(result)

    def update_pipeline(self) -> ActionResult:
        pipeline = self.codepipeline_backend.update_pipeline(
            self._get_param("pipeline")
        )

        return ActionResult({"pipeline": pipeline})

    def list_pipelines(self) -> ActionResult:
        pipelines = self.codepipeline_backend.list_pipelines()
        result = {
            "pipelines": [
                {
                    "name": codepipeline.pipeline["name"],
                    "version": codepipeline.pipeline["version"],
                    "created": codepipeline.created,
                    "updated": codepipeline.updated,
                }
                for codepipeline in pipelines
            ]
        }
        return ActionResult(result)

    def delete_pipeline(self) -> ActionResult:
        self.codepipeline_backend.delete_pipeline(self._get_param("name"))

        return EmptyResult()

    def list_tags_for_resource(self) -> ActionResult:
        tags = self.codepipeline_backend.list_tags_for_resource(
            self._get_param("resourceArn")
        )

        return ActionResult({"tags": tags})

    def tag_resource(self) -> ActionResult:
        self.codepipeline_backend.tag_resource(
            self._get_param("resourceArn"), self._get_param("tags")
        )

        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        self.codepipeline_backend.untag_resource(
            self._get_param("resourceArn"), self._get_param("tagKeys")
        )

        return EmptyResult()
