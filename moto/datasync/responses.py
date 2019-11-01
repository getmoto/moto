import json
import logging
import re

from moto.core.responses import BaseResponse
from six.moves.urllib.parse import urlparse

from .models import datasync_backends


class DataSyncResponse(BaseResponse):

    # TODO BJORN check datasync rege
    region_regex = re.compile(r"://(.+?)\.datasync\.amazonaws\.com")

    @property
    def datasync_backend(self):
        return datasync_backends[self.region]

    def list_locations(self):
        locations = list()
        for arn, location in self.datasync_backend.locations.items():
            locations.append( {
                'LocationArn': location.arn,
                'LocationUri': location.uri
             })

        return json.dumps({"Locations": locations})
    
    def create_location_s3(self):
        # s3://bucket_name/folder/
        s3_bucket_arn = self._get_param("S3BucketArn")
        subdirectory = self._get_param("Subdirectory")
        
        location_uri_elts = ['s3:/', s3_bucket_arn.split(':')[-1]]
        if subdirectory:
            location_uri_elts.append(subdirectory)
        location_uri='/'.join(location_uri_elts)
        arn = self.datasync_backend.create_location(location_uri)
        
        return json.dumps({'LocationArn':arn})


    def create_location_smb(self):
        # smb://smb.share.fqdn/AWS_Test/
        subdirectory = self._get_param("Subdirectory")
        server_hostname = self._get_param("ServerHostname")

        location_uri = '/'.join(['smb:/', server_hostname, subdirectory])
        arn = self.datasync_backend.create_location(location_uri)
        
        return json.dumps({'LocationArn':arn})


    def create_task(self):
        destination_location_arn = self._get_param("DestinationLocationArn")
        source_location_arn = self._get_param("SourceLocationArn")
        name = self._get_param("Name")

        arn = self.datasync_backend.create_task(
            source_location_arn,
            destination_location_arn,
            name
        )

        return json.dumps({'TaskArn':arn})

    def list_tasks(self):
        tasks = list()
        for arn, task in self.datasync_backend.tasks.items():
            tasks.append( {
                'Name': task.name,
                'Status': task.status,
                'TaskArn': task.arn
             })

        return json.dumps({"Tasks": tasks})

    def describe_task(self):
        task_arn = self._get_param("TaskArn")
        if task_arn in self.datasync_backend.tasks:
            task = self.datasync_backend.tasks[task_arn]
            return json.dumps({
                'TaskArn': task.arn,
                'Name': task.name,
                'Status': task.status,
                'SourceLocationArn': task.source_location_arn,
                'DestinationLocationArn': task.destination_location_arn
            })
        # TODO BJORN exception if task_arn not found?
        return None

    def start_task_execution(self):
        task_arn = self._get_param("TaskArn")
        if task_arn in self.datasync_backend.tasks:
            arn = self.datasync_backend.start_task_execution(
                task_arn
            )
            return json.dumps({'TaskExecutionArn':arn})

        # TODO BJORN exception if task_arn not found?
        return None
