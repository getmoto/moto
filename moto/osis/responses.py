"""Handles incoming osis requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import OpenSearchIngestionBackend, osis_backends


class OpenSearchIngestionResponse(BaseResponse):
    """Handler for OpenSearchIngestion requests and responses."""

    def __init__(self):
        super().__init__(service_name="osis")

    @property
    def osis_backend(self) -> OpenSearchIngestionBackend:
        """Return backend instance specific for this region."""
        return osis_backends[self.current_account][self.region]

    # add methods from here

    def create_pipeline(self):
        params = json.loads(self.body)
        pipeline_name = params.get("PipelineName")
        min_units = params.get("MinUnits")
        max_units = params.get("MaxUnits")
        pipeline_configuration_body = params.get("PipelineConfigurationBody")
        log_publishing_options = params.get("LogPublishingOptions")
        vpc_options = params.get("VpcOptions")
        buffer_options = params.get("BufferOptions")
        encryption_at_rest_options = params.get("EncryptionAtRestOptions")
        tags = params.get("Tags")
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
        # TODO: adjust response
        return json.dumps(dict(Pipeline=pipeline.to_dict()))

    def delete_pipeline(self):
        params = self._get_params()
        pipeline_name = params.get("PipelineName")
        self.osis_backend.delete_pipeline(
            pipeline_name=pipeline_name,
        )
        # TODO: adjust response
        return json.dumps(dict())

    # add templates from here

    def get_pipeline(self):
        params = self._get_params()
        pipeline_name = params.get("PipelineName")
        pipeline = self.osis_backend.get_pipeline(
            pipeline_name=pipeline_name,
        )
        # TODO: adjust response
        return json.dumps(dict(pipeline=pipeline))

    def list_pipelines(self):
        params = self._get_params()
        max_results = params.get("MaxResults")
        next_token = params.get("NextToken")
        next_token, pipelines = self.osis_backend.list_pipelines(
            max_results=max_results,
            next_token=next_token,
        )
        return json.dumps(dict(nextToken=next_token, Pipelines=pipelines))

    def list_tags_for_resource(self):
        params = self._get_params()
        arn = params.get("Arn")
        tags = self.osis_backend.list_tags_for_resource(
            arn=arn,
        )
        # TODO: adjust response
        return json.dumps(dict(tags=tags))

    def update_pipeline(self):
        params = self._get_params()
        pipeline_name = params.get("PipelineName")
        min_units = params.get("MinUnits")
        max_units = params.get("MaxUnits")
        pipeline_configuration_body = params.get("PipelineConfigurationBody")
        log_publishing_options = params.get("LogPublishingOptions")
        buffer_options = params.get("BufferOptions")
        encryption_at_rest_options = params.get("EncryptionAtRestOptions")
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
        return json.dumps(dict(pipeline=pipeline))

    def tag_resource(self):
        params = self._get_params()
        arn = params.get("Arn")
        tags = params.get("Tags")
        self.osis_backend.tag_resource(
            arn=arn,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def untag_resource(self):
        params = self._get_params()
        arn = params.get("Arn")
        tag_keys = params.get("TagKeys")
        self.osis_backend.untag_resource(
            arn=arn,
            tag_keys=tag_keys,
        )
        # TODO: adjust response
        return json.dumps(dict())

    def start_pipeline(self):
        params = self._get_params()
        pipeline_name = params.get("PipelineName")
        pipeline = self.osis_backend.start_pipeline(
            pipeline_name=pipeline_name,
        )
        # TODO: adjust response
        return json.dumps(dict(pipeline=pipeline))
