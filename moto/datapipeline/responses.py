from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import datapipeline_backends


class DataPipelineResponse(BaseResponse):
    @property
    def parameters(self):
        # TODO this should really be moved to core/responses.py
        if self.body:
            return json.loads(self.body)
        else:
            return self.querystring

    @property
    def datapipeline_backend(self):
        return datapipeline_backends[self.region]

    def create_pipeline(self):
        name = self.parameters.get("name")
        unique_id = self.parameters.get("uniqueId")
        description = self.parameters.get("description", "")
        tags = self.parameters.get("tags", [])
        pipeline = self.datapipeline_backend.create_pipeline(
            name, unique_id, description=description, tags=tags
        )
        return json.dumps({"pipelineId": pipeline.pipeline_id})

    def list_pipelines(self):
        pipelines = list(self.datapipeline_backend.list_pipelines())
        pipeline_ids = [pipeline.pipeline_id for pipeline in pipelines]
        max_pipelines = 50
        marker = self.parameters.get("marker")
        if marker:
            start = pipeline_ids.index(marker) + 1
        else:
            start = 0
        pipelines_resp = pipelines[start : start + max_pipelines]
        has_more_results = False
        marker = None
        if start + max_pipelines < len(pipeline_ids) - 1:
            has_more_results = True
            marker = pipelines_resp[-1].pipeline_id
        return json.dumps(
            {
                "hasMoreResults": has_more_results,
                "marker": marker,
                "pipelineIdList": [
                    pipeline.to_meta_json() for pipeline in pipelines_resp
                ],
            }
        )

    def describe_pipelines(self):
        pipeline_ids = self.parameters["pipelineIds"]
        pipelines = self.datapipeline_backend.describe_pipelines(pipeline_ids)

        return json.dumps(
            {"pipelineDescriptionList": [pipeline.to_json() for pipeline in pipelines]}
        )

    def delete_pipeline(self):
        pipeline_id = self.parameters["pipelineId"]
        self.datapipeline_backend.delete_pipeline(pipeline_id)
        return json.dumps({})

    def put_pipeline_definition(self):
        pipeline_id = self.parameters["pipelineId"]
        pipeline_objects = self.parameters["pipelineObjects"]

        self.datapipeline_backend.put_pipeline_definition(pipeline_id, pipeline_objects)
        return json.dumps({"errored": False})

    def get_pipeline_definition(self):
        pipeline_id = self.parameters["pipelineId"]
        pipeline_definition = self.datapipeline_backend.get_pipeline_definition(
            pipeline_id
        )
        return json.dumps(
            {
                "pipelineObjects": [
                    pipeline_object.to_json() for pipeline_object in pipeline_definition
                ]
            }
        )

    def describe_objects(self):
        pipeline_id = self.parameters["pipelineId"]
        object_ids = self.parameters["objectIds"]

        pipeline_objects = self.datapipeline_backend.describe_objects(
            object_ids, pipeline_id
        )
        return json.dumps(
            {
                "hasMoreResults": False,
                "marker": None,
                "pipelineObjects": [
                    pipeline_object.to_json() for pipeline_object in pipeline_objects
                ],
            }
        )

    def activate_pipeline(self):
        pipeline_id = self.parameters["pipelineId"]
        self.datapipeline_backend.activate_pipeline(pipeline_id)
        return json.dumps({})
