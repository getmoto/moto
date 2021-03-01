from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel


class MediaPackageBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaPackageBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_channel(self, description, id, tags):
        # implement here
        return arn, description, egress_access_logs, hls_ingest, id, ingress_access_logs, tags
    
    def describe_channel(self, id):
        # implement here
        return arn, description, egress_access_logs, hls_ingest, id, ingress_access_logs, tags
    
    # add methods from here


mediapackage_backends = {}
for region in Session().get_available_regions("mediapackage"):
    mediapackage_backends[region] = MediaPackageBackend()
for region in Session().get_available_regions("mediapackage", partition_name="aws-us-gov"):
    mediapackage_backends[region] = MediaPackageBackend()
for region in Session().get_available_regions("mediapackage", partition_name="aws-cn"):
    mediapackage_backends[region] = MediaPackageBackend()
