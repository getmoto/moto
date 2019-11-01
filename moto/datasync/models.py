import json
import logging
import random
import string

import boto3
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel


class Location(BaseModel):

    def __init__(self,
                location_uri,
                region_name,
                arn_counter=0):
        self.uri = location_uri
        self.region_name = region_name
        # Generate ARN
        self.arn = 'arn:aws:datasync:{0}:111222333444:location/loc-{1}'.format(region_name, str(arn_counter).zfill(17))


class Task(BaseModel):
    def __init__(self,
                 source_location_arn,
                 destination_location_arn,
                 name,
                 region_name,
                 arn_counter=0):
        self.source_location_arn = source_location_arn
        self.destination_location_arn = destination_location_arn
        self.status = 'AVAILABLE'
        self.name = name
        # Generate ARN
        self.arn = 'arn:aws:datasync:{0}:111222333444:task/task-{1}'.format(region_name, str(arn_counter).zfill(17))

class TaskExecution(BaseModel):
    def __init__(self, 
                 task_arn,
                 arn_counter=0):
        self.task_arn = task_arn
        self.arn = '{0}/execution/exec-{1}'.format(task_arn, str(arn_counter).zfill(17))

class DataSyncBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        # Always increase when new things are created
        # This ensures uniqueness
        self.arn_counter = 0 
        self.locations = dict()
        self.tasks = dict()
        self.task_executions = dict()
        
    def reset(self):
        region_name = self.region_name
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region_name)

    def create_location(self, location_uri):
        # TODO BJORN figure out exception
        # TODO BJORN test for exception
        for arn, location in self.locations.items():
            if location.uri == location_uri:
                raise Exception('Location already exists')
        self.arn_counter = self.arn_counter + 1
        location = Location(location_uri,
                            region_name=self.region_name,
                            arn_counter=self.arn_counter)
        self.locations[location.arn] = location
        return location.arn

    def create_task(self,
                    source_location_arn,
                    destination_location_arn,
                    name):
        self.arn_counter = self.arn_counter + 1
        task = Task(source_location_arn,
                    destination_location_arn,
                    name,
                    region_name=self.region_name,
                    arn_counter=self.arn_counter
                    )
        self.tasks[task.arn] = task
        return task.arn

    def start_task_execution(self, task_arn):
        self.arn_counter = self.arn_counter + 1
        task_execution = TaskExecution(task_arn,
                                       arn_counter=self.arn_counter)
        self.task_executions[task_execution.arn] = task_execution
        return task_execution.arn

datasync_backends = {}
for region in boto3.Session().get_available_regions("datasync"):
    datasync_backends[region] = DataSyncBackend(region_name=region)
