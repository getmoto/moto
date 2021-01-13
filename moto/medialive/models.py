from __future__ import unicode_literals
from uuid import uuid4
from boto3 import Session
from moto.core import BaseBackend


class Channel:
    def __init__(self, *args, **kwargs):
        self.arn = kwargs.get("arn")
        self.cdi_input_specification = kwargs.get("cdi_input_specification")
        self.channel_class = kwargs.get("channel_class", "STANDARD")
        self.destinations = kwargs.get("destinations")
        self.egress_endpoints = kwargs.get("egress_endpoints", [])
        self.encoder_settings = kwargs.get("encoder_settings")
        self.channel_id = kwargs.get("channel_id")
        self.input_attachments = kwargs.get("input_attachments")
        self.input_specification = kwargs.get("input_specification")
        self.log_level = kwargs.get("log_level")
        self.name = kwargs.get("name")
        self.pipeline_details = kwargs.get("pipeline_details", [])
        self.role_arn = kwargs.get("role_arn")
        self.state = kwargs.get("state")
        self.tags = kwargs.get("tags")
        self._previous_state = None

    def to_dict(self, exclude=None):
        data = {
            "arn": self.arn,
            "cdiInputSpecification": self.cdi_input_specification,
            "channelClass": self.channel_class,
            "destinations": self.destinations,
            "egressEndpoints": self.egress_endpoints,
            "encoderSettings": self.encoder_settings,
            "id": self.channel_id,
            "inputAttachments": self.input_attachments,
            "inputSpecification": self.input_specification,
            "logLevel": self.log_level,
            "name": self.name,
            "pipelineDetails": self.pipeline_details,
            "pipelinesRunningCount": 1
            if self.channel_class == "SINGLE_PIPELINE"
            else 2,
            "roleArn": self.role_arn,
            "state": self.state,
            "tags": self.tags,
        }
        if exclude:
            for key in exclude:
                del data[key]
        return data

    def _resolve_transient_states(self):
        # Resolve transient states before second call
        # (to simulate AWS taking its sweet time with these things)
        if self.state in ["CREATING", "STOPPING"]:
            self.state = "IDLE"
        elif self.state == "STARTING":
            self.state = "RUNNING"
        elif self.state == "DELETING":
            self.state = "DELETED"
        elif self.state == "UPDATING":
            self.state = self._previous_state
            self._previous_state = None


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
        channel = Channel(
            arn=arn,
            cdi_input_specification=cdi_input_specification,
            channel_class=channel_class or "STANDARD",
            destinations=destinations,
            egress_endpoints=[],
            encoder_settings=encoder_settings,
            channel_id=channel_id,
            input_attachments=input_attachments,
            input_specification=input_specification,
            log_level=log_level,
            name=name,
            pipeline_details=[],
            role_arn=role_arn,
            state="CREATING",
            tags=tags,
        )
        self._channels[channel_id] = channel
        return channel

    def list_channels(self, max_results, next_token):
        channels = list(self._channels.values())
        if max_results is not None:
            channels = channels[:max_results]
        response_channels = [
            c.to_dict(exclude=["encoderSettings", "pipelineDetails"]) for c in channels
        ]
        return response_channels, next_token

    def describe_channel(self, channel_id):
        channel = self._channels[channel_id]
        channel._resolve_transient_states()
        return channel.to_dict()

    def delete_channel(self, channel_id):
        channel = self._channels[channel_id]
        channel.state = "DELETING"
        return channel.to_dict()

    def start_channel(self, channel_id):
        channel = self._channels[channel_id]
        channel.state = "STARTING"
        return channel.to_dict()

    def stop_channel(self, channel_id):
        channel = self._channels[channel_id]
        channel.state = "STOPPING"
        return channel.to_dict()

    def update_channel(
        self,
        channel_id,
        cdi_input_specification,
        destinations,
        encoder_settings,
        input_attachments,
        input_specification,
        log_level,
        name,
        role_arn,
    ):
        channel = self._channels[channel_id]
        channel.cdi_input_specification = cdi_input_specification
        channel.destinations = destinations
        channel.encoder_settings = encoder_settings
        channel.input_attachments = input_attachments
        channel.input_specification = input_specification
        channel.log_level = log_level
        channel.name = name
        channel.role_arn = role_arn

        channel._resolve_transient_states()
        channel._previous_state = channel.state
        channel.state = "UPDATING"

        return channel


medialive_backends = {}
for region in Session().get_available_regions("medialive"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-us-gov"):
    medialive_backends[region] = MediaLiveBackend()
for region in Session().get_available_regions("medialive", partition_name="aws-cn"):
    medialive_backends[region] = MediaLiveBackend()
