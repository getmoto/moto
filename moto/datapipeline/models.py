from __future__ import unicode_literals

import datetime
import boto.datapipeline
from moto.core import BaseBackend
from .utils import get_random_pipeline_id


class PipelineObject(object):
    def __init__(self, object_id, name, fields):
        self.object_id = object_id
        self.name = name
        self.fields = fields

    def to_json(self):
        return {
            "Fields": self.fields,
            "Id": self.object_id,
            "Name": self.name,
        }


class Pipeline(object):
    def __init__(self, name, unique_id):
        self.name = name
        self.unique_id = unique_id
        self.description = ""
        self.pipeline_id = get_random_pipeline_id()
        self.creation_time = datetime.datetime.utcnow()
        self.objects = []
        self.status = "PENDING"

    def to_json(self):
        return {
            "Description": self.description,
            "Fields": [{
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
            "Name": self.name,
            "PipelineId": self.pipeline_id,
            "Tags": [
            ]
        }

    def set_pipeline_objects(self, pipeline_objects):
        self.objects = [
            PipelineObject(pipeline_object['id'], pipeline_object['name'], pipeline_object['fields'])
            for pipeline_object in pipeline_objects
        ]

    def activate(self):
        self.status = "SCHEDULED"


class DataPipelineBackend(BaseBackend):

    def __init__(self):
        self.pipelines = {}

    def create_pipeline(self, name, unique_id):
        pipeline = Pipeline(name, unique_id)
        self.pipelines[pipeline.pipeline_id] = pipeline
        return pipeline

    def list_pipelines(self):
        return self.pipelines.values()

    def describe_pipelines(self, pipeline_ids):
        pipelines = [pipeline for pipeline in self.pipelines.values() if pipeline.pipeline_id in pipeline_ids]
        return pipelines

    def get_pipeline(self, pipeline_id):
        return self.pipelines[pipeline_id]

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
