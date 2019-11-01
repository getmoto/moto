import json
import logging
import random
import string

import boto3
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel


'''
Endpoints I need to test:

list_locations
list_tasks
start_task_execution
cancel_task_execution
describe_task
describe_task_execution
'''


def datasync_json_dump(datasync_object):
    return json.dumps(datasync_object)

class Location(BaseModel):
    def __init__(self, location_uri, region_name):
        self.location_uri = location_uri
        self.region_name = region_name
        loc = ''.join([random.choice(string.ascii_lowercase + string.digits) for _ in range(17)])
        self.arn = 'arn:aws:datasync:{0}:111222333444:location/loc-{1}'.format(region_name, loc)


class DataSyncBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        self.locations = OrderedDict()
    
    def reset(self):
        region_name = self.region_name
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region_name)

    def create_location(self, location_uri):
        if location_uri in self.locations:
            raise Exception('Location already exists')
        
        location = Location(location_uri, region_name=self.region_name)
        self.locations['location_uri'] = location
        return location.arn


datasync_backends = {}
for region in boto3.Session().get_available_regions("datasync"):
    datasync_backends[region] = DataSyncBackend(region_name=region)
