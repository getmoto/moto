from __future__ import unicode_literals
from uuid import uuid4
from boto3 import Session
from moto.core import BaseBackend


class MediaLiveBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaLiveBackend, self).__init__()
        self.region_name = region_name
        self._channels = {}

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
        channel_id = uuid4().hex
        arn = "arn:aws:medialive:channel:{}".format(channel_id)
        channel = {
            "arn": arn,
            "cdiInputSpecification": cdi_input_specification,
            "channelClass": channel_class or "STANDARD",
            "destinations": destinations,
            "egressEndpoints": [],
            "encoderSettings": encoder_settings,
            "id": channel_id,
            "inputAttachments": input_attachments,
            "inputSpecification": input_specification,
            "logLevel": log_level,
            "name": name,
            "pipelineDetails": [],
            "roleArn": role_arn,
            "state": "CREATING",
            "tags": tags,
        }
        self._channels[channel_id] = channel
        return channel


medialive_backends = {}
for region in Session().get_available_regions("medialive"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-us-gov"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-cn"):
    medialive_backends[region] = MediaLiveBackend()
