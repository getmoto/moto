from __future__ import unicode_literals

import datetime
import boto.datapipeline
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from .utils import get_random_pipeline_id, remove_capitalization_of_dict_keys


class PipelineObject(BaseModel):

    def __init__(self, object_id, name, fields):
        self.object_id = object_id
        self.name = name
        self.fields = fields

    def to_json(self):
        return {
            "fields": self.fields,
            "id": self.object_id,
            "name": self.name,
        }


class Pipeline(BaseModel):

    def __init__(self, name, unique_id, **kwargs):
        self.name = name
        self.unique_id = unique_id
        self.description = kwargs.get('description', '')
        self.pipeline_id = get_random_pipeline_id()
        self.creation_time = datetime.datetime.utcnow()
        self.objects = []
        self.status = "PENDING"
        self.tags = kwargs.get('tags', [])

    @property
    def physical_resource_id(self):
        return self.pipeline_id

    def to_meta_json(self):
        return {
            "id": self.pipeline_id,
            "name": self.name,
        }

    def to_json(self):
        return {
            "description": self.description,
            "fields": [{
                "key": "@pipelineState",
                "stringValue": self.status,
            }, {
                "key": "description",
                "stringValue": self.description
            }, {
                "key": "name",
                "stringValue": self.name
            }, {
                "key": "@creationTime",
                "stringValue": datetime.datetime.strftime(self.creation_time, '%Y-%m-%dT%H-%M-%S'),
            }, {
                "key": "@id",
                "stringValue": self.pipeline_id,
            }, {
                "key": "@sphere",
                "stringValue": "PIPELINE"
            }, {
                "key": "@version",
                "stringValue": "1"
            }, {
                "key": "@userId",
                "stringValue": "924374875933"
            }, {
                "key": "@accountId",
                "stringValue": "924374875933"
            }, {
                "key": "uniqueId",
                "stringValue": self.unique_id
            }],
            "name": self.name,
            "pipelineId": self.pipeline_id,
            "tags": self.tags
        }

    def set_pipeline_objects(self, pipeline_objects):
        self.objects = [
            PipelineObject(pipeline_object['id'], pipeline_object[
                           'name'], pipeline_object['fields'])
            for pipeline_object in remove_capitalization_of_dict_keys(pipeline_objects)
        ]

    def activate(self):
        self.status = "SCHEDULED"

    @classmethod
    def create_from_cloudformation_json(cls, resource_name, cloudformation_json, region_name):
        datapipeline_backend = datapipeline_backends[region_name]
        properties = cloudformation_json["Properties"]

        cloudformation_unique_id = "cf-" + properties["Name"]
        pipeline = datapipeline_backend.create_pipeline(
            properties["Name"], cloudformation_unique_id)
        datapipeline_backend.put_pipeline_definition(
            pipeline.pipeline_id, properties["PipelineObjects"])

        if properties["Activate"]:
            pipeline.activate()
        return pipeline


class DataPipelineBackend(BaseBackend):

    def __init__(self):
        self.pipelines = OrderedDict()

    def create_pipeline(self, name, unique_id, **kwargs):
        pipeline = Pipeline(name, unique_id, **kwargs)
        self.pipelines[pipeline.pipeline_id] = pipeline
        return pipeline

    def list_pipelines(self):
        return self.pipelines.values()

    def describe_pipelines(self, pipeline_ids):
        pipelines = [pipeline for pipeline in self.pipelines.values(
        ) if pipeline.pipeline_id in pipeline_ids]
        return pipelines

    def get_pipeline(self, pipeline_id):
        return self.pipelines[pipeline_id]

    def delete_pipeline(self, pipeline_id):
        self.pipelines.pop(pipeline_id, None)

    def put_pipeline_definition(self, pipeline_id, pipeline_objects):
        pipeline = self.get_pipeline(pipeline_id)
        pipeline.set_pipeline_objects(pipeline_objects)

    def get_pipeline_definition(self, pipeline_id):
        pipeline = self.get_pipeline(pipeline_id)
        return pipeline.objects

    def describe_objects(self, object_ids, pipeline_id):
        pipeline = self.get_pipeline(pipeline_id)
        pipeline_objects = [
            pipeline_object for pipeline_object in pipeline.objects
            if pipeline_object.object_id in object_ids
        ]
        return pipeline_objects

    def activate_pipeline(self, pipeline_id):
        pipeline = self.get_pipeline(pipeline_id)
        pipeline.activate()


datapipeline_backends = {}
for region in boto.datapipeline.regions():
    datapipeline_backends[region.name] = DataPipelineBackend()
