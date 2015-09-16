from __future__ import unicode_literals

import json

from moto.core.responses import BaseResponse
from .models import datapipeline_backends


class DataPipelineResponse(BaseResponse):

    @property
    def parameters(self):
        return json.loads(self.body.decode("utf-8"))

    @property
    def datapipeline_backend(self):
        return datapipeline_backends[self.region]

    def create_pipeline(self):
        name = self.parameters['name']
        unique_id = self.parameters['uniqueId']
        pipeline = self.datapipeline_backend.create_pipeline(name, unique_id)
        return json.dumps({
            "pipelineId": pipeline.pipeline_id,
        })

    def describe_pipelines(self):
        pipeline_ids = self.parameters["pipelineIds"]
        pipelines = self.datapipeline_backend.describe_pipelines(pipeline_ids)

        return json.dumps({
            "PipelineDescriptionList": [
                pipeline.to_json() for pipeline in pipelines
            ]
        })

    def put_pipeline_definition(self):
        pipeline_id = self.parameters["pipelineId"]
        pipeline_objects = self.parameters["pipelineObjects"]

        self.datapipeline_backend.put_pipeline_definition(pipeline_id, pipeline_objects)
        return json.dumps({"errored": False})

    def get_pipeline_definition(self):
        pipeline_id = self.parameters["pipelineId"]
        pipeline_definition = self.datapipeline_backend.get_pipeline_definition(pipeline_id)
        return json.dumps({
            "pipelineObjects": [pipeline_object.to_json() for pipeline_object in pipeline_definition]
        })

    def describe_objects(self):
        pipeline_id = self.parameters["pipelineId"]
        object_ids = self.parameters["objectIds"]

        pipeline_objects = self.datapipeline_backend.describe_objects(object_ids, pipeline_id)

        return json.dumps({
            "HasMoreResults": False,
            "Marker": None,
            "PipelineObjects": [
                pipeline_object.to_json() for pipeline_object in pipeline_objects
            ]
        })

    def activate_pipeline(self):
        pipeline_id = self.parameters["pipelineId"]
        self.datapipeline_backend.activate_pipeline(pipeline_id)
        return json.dumps({})
