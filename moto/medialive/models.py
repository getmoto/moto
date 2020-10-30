from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel


class MediaLiveBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaLiveBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_channel(
        self,
        cdi_input_specification,
        channel_class,
        destinations,
        encoder_settings,
        input_attachments,
        input_specification,
        log_level,
        name,
        request_id,
        reserved,
        role_arn,
        tags,
    ):
        # implement here
        channel = {
            "Name": name,
            "Tags": tags,
        }
        return channel

    # add methods from here


medialive_backends = {}
for region in Session().get_available_regions("medialive"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-us-gov"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-cn"):
    medialive_backends[region] = MediaLiveBackend()
