import typing

from moto.s3.models import s3_backends
import json
from typing import Any, Dict
from .exceptions import ValidationError

if typing.TYPE_CHECKING:
    from .models import FakePipeline, FakePipelineExecution


def get_pipeline_from_name(
    pipelines: Dict[str, "FakePipeline"], pipeline_name: str
) -> "FakePipeline":
    try:
        return pipelines[pipeline_name]
    except KeyError:
        raise ValidationError(
            message=f"Could not find pipeline with PipelineName {pipeline_name}."
        )


def get_pipeline_name_from_execution_arn(pipeline_execution_arn: str) -> str:
    return pipeline_execution_arn.split("/")[1].split(":")[-1]


def get_pipeline_execution_from_arn(
    pipelines: Dict[str, "FakePipeline"], pipeline_execution_arn: str
) -> "FakePipelineExecution":
    try:
        pipeline_name = get_pipeline_name_from_execution_arn(pipeline_execution_arn)
        pipeline = get_pipeline_from_name(pipelines, pipeline_name)
        return pipeline.pipeline_executions[pipeline_execution_arn]
    except KeyError:
        raise ValidationError(
            message=f"Could not find pipeline execution with PipelineExecutionArn {pipeline_execution_arn}."
        )


def load_pipeline_definition_from_s3(
    pipeline_definition_s3_location: Dict[str, Any], account_id: str
) -> Dict[str, Any]:
    s3_backend = s3_backends[account_id]["global"]
    result = s3_backend.get_object(
        bucket_name=pipeline_definition_s3_location["Bucket"],
        key_name=pipeline_definition_s3_location["ObjectKey"],
    )
    return json.loads(result.value)


def arn_formatter(_type: str, _id: str, account_id: str, region_name: str) -> str:
    return f"arn:aws:sagemaker:{region_name}:{account_id}:{_type}/{_id}"


def validate_model_approval_status(model_approval_status: typing.Optional[str]) -> None:
    if model_approval_status is not None and model_approval_status not in [
        "Approved",
        "Rejected",
        "PendingManualApproval",
    ]:
        raise ValidationError(
            f"Value '{model_approval_status}' at 'modelApprovalStatus' failed to satisfy constraint: "
            "Member must satisfy enum value set: [PendingManualApproval, Approved, Rejected]"
        )
