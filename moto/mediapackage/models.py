from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from uuid import uuid4
from collections import OrderedDict


class Channel(BaseModel):
    def __init__(self, *args, **kwargs):
        self.arn = kwargs.get("arn")
        self.channel_id = kwargs.get("channel_id")
        self.description = kwargs.get("description")
        self.tags = kwargs.get("tags")

    def to_dict(self, exclude=None):
        data = {
            "arn": self.arn,
            "id": self.channel_id,
            "description": self.description,
            "tags": self.tags,
        }
        if exclude:
            for key in exclude:
                del data[key]
        return data


class MediaPackageBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaPackageBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)
        self._channels = OrderedDict()

    def create_channel(self, description, id, tags):
        arn = "arn:aws:mediapackage:channel:{}".format(id)
        channel = Channel(
            arn=arn,
            description=description,
            egress_access_logs={},
            hls_ingest={},
            channel_id=id,
            ingress_access_logs={},
            tags=tags,
        )
        self._channels[id] = channel
        return channel
    
    def list_channels(self):
        channels = list(self._channels.values())
        response_channels = [
            c.to_dict() for c in channels
        ]
        return response_channels
    
    def describe_channel(self, id):
        channel = self._channels[id]
        return channel.to_dict()

    def describe_origin_endpoint(self, id):
        # implement here
        return arn, authorization, channel_id, cmaf_package, dash_package, description, hls_package, id, manifest_name, mss_package, origination, startover_window_seconds, tags, time_delay_seconds, url, whitelist
    
    def delete_channel(self, id):
        channel = self._channels[id]
        del self._channels[id]
        return channel.to_dict()

    

mediapackage_backends = {}
for region in Session().get_available_regions("mediapackage"):
    mediapackage_backends[region] = MediaPackageBackend()
for region in Session().get_available_regions("mediapackage", partition_name="aws-us-gov"):
    mediapackage_backends[region] = MediaPackageBackend()
for region in Session().get_available_regions("mediapackage", partition_name="aws-cn"):
    mediapackage_backends[region] = MediaPackageBackend()
