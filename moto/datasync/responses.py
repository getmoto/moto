import json
import logging
import re

from moto.core.responses import BaseResponse
from six.moves.urllib.parse import urlparse

from .models import datasync_backends


class DataSyncResponse(BaseResponse):

    region_regex = re.compile(r"://(.+?)\.datasync\.amazonaws\.com")

    @property
    def datasync_backend(self):
        return datasync_backends[self.region]

    def list_locations(self):
        locations = self.datasync_backend.locations
        logging.info('FOUND SOME SHIT {0}'.format(locations))
        
        template = self.response_template(LIST_LOCATIONS_RESPONSE)
        r = template.render(locations=locations)
        logging.info('list_locations r={0}'.format(r))
        return 'GARBAGE'
        return r

    
    def create_location_s3(self):
        # s3://bucket_name/folder/
        s3_bucket_arn = self._get_param("S3BucketArn")
        
        bucket_and_path = s3_bucket_arn.split(':')[-1]
        location_uri='/'.join(['s3:/', bucket_and_path])
        location = self.datasync_backend.create_location(location_uri)
        
        return json.dumps({'LocationArn':location})


    def create_location_smb(self):
        # smb://smb.share.fqdn/AWS_Test/
        subdirectory = self._get_param("Subdirectory")
        server_hostname = self._get_param("ServerHostname")

        location_uri = '/'.join(['smb:/', server_hostname, subdirectory])
        location = self.datasync_backend.create_location(location_uri)
        
        return json.dumps({'LocationArn':location})
