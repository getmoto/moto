"""Handles incoming osis requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import OpenSearchIngestionBackend, Pipeline, osis_backends


class OpenSearchIngestionResponse(BaseResponse):
    """Handler for OpenSearchIngestion requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="osis")
        self.automated_parameter_parsing = True

    @property
    def osis_backend(self) -> OpenSearchIngestionBackend:
        """Return backend instance specific for this region."""
        return osis_backends[self.current_account][self.region]

    def _pipeline_summary(self, pipeline: Pipeline) -> dict[str, Any]:
        return {
            "Status": pipeline.status,
            "StatusReason": {
                "Description": pipeline.STATUS_REASON_MAP.get(
                    pipeline.status or "", ""
                ),
            },
            "PipelineName": pipeline.pipeline_name,
            "PipelineArn": pipeline.arn,
            "MinUnits": pipeline.min_units,
            "MaxUnits": pipeline.max_units,
            "CreatedAt": pipeline.created_at,
            "LastUpdatedAt": pipeline.last_updated_at,
            "Destinations": pipeline.destinations,
            "Tags": self.osis_backend.list_tags_for_resource(pipeline.arn)["Tags"],
        }

    def _pipeline(self, pipeline: Pipeline) -> dict[str, Any]:
        return {
            **self._pipeline_summary(pipeline),
            "PipelineConfigurationBody": pipeline.pipeline_configuration_body_str,
            "IngestEndpointUrls": pipeline.ingest_endpoint_urls,
            "LogPublishingOptions": pipeline.log_publishing_options,
            "VpcEndpoints": None
            if pipeline.vpc_options is None
            else [
                {
                    "VpcEndpointId": pipeline.vpc_endpoint,
                    "VpcId": pipeline.vpc_id,
                    "VpcOptions": pipeline.vpc_options,
                }
            ],
            "BufferOptions": pipeline.buffer_options,
            "EncryptionAtRestOptions": pipeline.encryption_at_rest_options,
            "VpcEndpointService": pipeline.vpc_endpoint_service,
            "ServiceVpcEndpoints": pipeline.service_vpc_endpoints,
        }

    def create_pipeline(self) -> ActionResult:
        pipeline_name = self._get_param("PipelineName")
        min_units = self._get_param("MinUnits")
        max_units = self._get_param("MaxUnits")
        pipeline_configuration_body = self._get_param("PipelineConfigurationBody")
        log_publishing_options = self._get_param("LogPublishingOptions")
        vpc_options = self._get_param("VpcOptions")
        buffer_options = self._get_param("BufferOptions")
        encryption_at_rest_options = self._get_param("EncryptionAtRestOptions")
        tags = self._get_param("Tags")
        pipeline = self.osis_backend.create_pipeline(
            pipeline_name=pipeline_name,
            min_units=min_units,
            max_units=max_units,
            pipeline_configuration_body=pipeline_configuration_body,
            log_publishing_options=log_publishing_options,
            vpc_options=vpc_options,
            buffer_options=buffer_options,
            encryption_at_rest_options=encryption_at_rest_options,
            tags=tags,
        )
        return ActionResult({"Pipeline": self._pipeline(pipeline)})

    def delete_pipeline(self) -> EmptyResult:
        pipeline_name = self._get_param("PipelineName")
        self.osis_backend.delete_pipeline(
            pipeline_name=pipeline_name,
        )
        return EmptyResult()

    def get_pipeline(self) -> ActionResult:
        pipeline_name = self._get_param("PipelineName")
        pipeline = self.osis_backend.get_pipeline(
            pipeline_name=pipeline_name,
        )
        return ActionResult({"Pipeline": self._pipeline(pipeline)})

    def list_pipelines(self) -> ActionResult:
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken")
        pipelines, next_token = self.osis_backend.list_pipelines(
            max_results=max_results,
            next_token=next_token,
        )
        result = {
            "NextToken": next_token,
            "Pipelines": [self._pipeline_summary(p) for p in pipelines],
        }
        return ActionResult(result)

    def list_tags_for_resource(self) -> ActionResult:
        arn = self._get_param("Arn")
        tags = self.osis_backend.list_tags_for_resource(arn=arn)
        return ActionResult({"Tags": tags["Tags"]})

    def update_pipeline(self) -> ActionResult:
        pipeline_name = self._get_param("PipelineName")
        min_units = self._get_param("MinUnits")
        max_units = self._get_param("MaxUnits")
        pipeline_configuration_body = self._get_param("PipelineConfigurationBody")
        log_publishing_options = self._get_param("LogPublishingOptions")
        buffer_options = self._get_param("BufferOptions")
        encryption_at_rest_options = self._get_param("EncryptionAtRestOptions")
        pipeline = self.osis_backend.update_pipeline(
            pipeline_name=pipeline_name,
            min_units=min_units,
            max_units=max_units,
            pipeline_configuration_body=pipeline_configuration_body,
            log_publishing_options=log_publishing_options,
            buffer_options=buffer_options,
            encryption_at_rest_options=encryption_at_rest_options,
        )
        # TODO: adjust response
        return ActionResult({"Pipeline": self._pipeline(pipeline)})

    def tag_resource(self) -> EmptyResult:
        arn = self._get_param("Arn")
        tags = self._get_param("Tags")
        self.osis_backend.tag_resource(
            arn=arn,
            tags=tags,
        )
        return EmptyResult()

    def untag_resource(self) -> EmptyResult:
        arn = self._get_param("Arn")
        tag_keys = self._get_param("TagKeys")
        self.osis_backend.untag_resource(
            arn=arn,
            tag_keys=tag_keys,
        )
        return EmptyResult()

    def start_pipeline(self) -> ActionResult:
        pipeline_name = self._get_param("PipelineName")
        pipeline = self.osis_backend.start_pipeline(
            pipeline_name=pipeline_name,
        )
        return ActionResult({"Pipeline": self._pipeline(pipeline)})

    def stop_pipeline(self) -> ActionResult:
        pipeline_name = self._get_param("PipelineName")
        pipeline = self.osis_backend.stop_pipeline(
            pipeline_name=pipeline_name,
        )
        return ActionResult({"Pipeline": self._pipeline(pipeline)})

    def get_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        policy = self.osis_backend.get_resource_policy(
            resource_arn=resource_arn,
        )
        return ActionResult({"ResourceArn": resource_arn, "Policy": policy})

    def put_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        policy = self._get_param("Policy")
        self.osis_backend.put_resource_policy(
            resource_arn=resource_arn,
            policy=policy,
        )
        return ActionResult({"ResourceArn": resource_arn, "Policy": policy})

    def delete_resource_policy(self) -> EmptyResult:
        resource_arn = self._get_param("ResourceArn")
        self.osis_backend.delete_resource_policy(
            resource_arn=resource_arn,
        )
        return EmptyResult()
