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

    def list_channels(self, max_results, next_token):
        channels = list(self._channels.values())
        if max_results is not None:
            channels = channels[:max_results]
        response_channels = []
        for channel in channels:
            response_channels.append(
                {
                    "arn": channel["arn"],
                    "cdiInputSpecification": channel["cdiInputSpecification"],
                    "channelClass": channel["channelClass"],
                    "destinations": channel["destinations"],
                    "egressEndpoints": channel["egressEndpoints"],
                    "id": channel["id"],
                    "inputAttachments": channel["inputAttachments"],
                    "inputSpecification": channel["inputSpecification"],
                    "logLevel": channel["logLevel"],
                    "name": channel["name"],
                    "pipelinesRunningCount": 1
                    if channel["channelClass"] == "SINGLE_PIPELINE"
                    else 2,
                    "roleArn": channel["roleArn"],
                    "state": channel["state"],
                    "tags": channel["tags"],
                }
            )
        return response_channels, next_token

    def describe_channel(self, channel_id):
        channel = self._channels[channel_id]
        return (
            channel["arn"],
            channel["cdiInputSpecification"],
            channel["channelClass"],
            channel["destinations"],
            channel["egressEndpoints"],
            channel["encoderSettings"],
            channel["id"],
            channel["inputAttachments"],
            channel["inputSpecification"],
            channel["logLevel"],
            channel["name"],
            channel["pipelineDetails"],
            1 if channel["channelClass"] == "SINGLE_PIPELINE" else 2,
            channel["roleArn"],
            channel["state"],
            channel["tags"],
        )

    def delete_channel(self, channel_id):
        channel = self._channels[channel_id]
        channel["state"] = "DELETED"
        return (
            channel["arn"],
            channel["cdiInputSpecification"],
            channel["channelClass"],
            channel["destinations"],
            channel["egressEndpoints"],
            channel["encoderSettings"],
            channel["id"],
            channel["inputAttachments"],
            channel["inputSpecification"],
            channel["logLevel"],
            channel["name"],
            channel["pipelineDetails"],
            1 if channel["channelClass"] == "SINGLE_PIPELINE" else 2,
            channel["roleArn"],
            channel["state"],
            channel["tags"],
        )


medialive_backends = {}
for region in Session().get_available_regions("medialive"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-us-gov"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-cn"):
    medialive_backends[region] = MediaLiveBackend()
