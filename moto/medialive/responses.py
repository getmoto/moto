from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import medialive_backends
import json


class MediaLiveResponse(BaseResponse):
    SERVICE_NAME = "medialive"

    @property
    def medialive_backend(self):
        return medialive_backends[self.region]

    def create_channel(self):
        cdi_input_specification = self._get_param("cdiInputSpecification")
        channel_class = self._get_param("channelClass")
        destinations = self._get_param("destinations")
        encoder_settings = self._get_param("encoderSettings")
        input_attachments = self._get_param("inputAttachments")
        input_specification = self._get_param("inputSpecification")
        log_level = self._get_param("logLevel")
        name = self._get_param("name")
        request_id = self._get_param("requestId")
        reserved = self._get_param("reserved")
        role_arn = self._get_param("roleArn")
        tags = self._get_param("tags")
        channel = self.medialive_backend.create_channel(
            cdi_input_specification=cdi_input_specification,
            channel_class=channel_class,
            destinations=destinations,
            encoder_settings=encoder_settings,
            input_attachments=input_attachments,
            input_specification=input_specification,
            log_level=log_level,
            name=name,
            request_id=request_id,
            reserved=reserved,
            role_arn=role_arn,
            tags=tags,
        )

        return json.dumps(
            dict(channel=channel.to_dict(exclude=["pipelinesRunningCount"]))
        )

    def list_channels(self):
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        channels, next_token = self.medialive_backend.list_channels(
            max_results=max_results, next_token=next_token,
        )

        return json.dumps(dict(channels=channels, nextToken=next_token))

    def describe_channel(self):
        channel_id = self._get_param("channelId")
        return json.dumps(
            self.medialive_backend.describe_channel(channel_id=channel_id,)
        )

    def delete_channel(self):
        channel_id = self._get_param("channelId")
        return json.dumps(self.medialive_backend.delete_channel(channel_id=channel_id,))

    def start_channel(self):
        channel_id = self._get_param("channelId")
        return json.dumps(self.medialive_backend.start_channel(channel_id=channel_id,))

    def stop_channel(self):
        channel_id = self._get_param("channelId")
        return json.dumps(self.medialive_backend.stop_channel(channel_id=channel_id,))

    def update_channel(self):
        channel_id = self._get_param("channelId")
        cdi_input_specification = self._get_param("cdiInputSpecification")
        destinations = self._get_param("destinations")
        encoder_settings = self._get_param("encoderSettings")
        input_attachments = self._get_param("inputAttachments")
        input_specification = self._get_param("inputSpecification")
        log_level = self._get_param("logLevel")
        name = self._get_param("name")
        role_arn = self._get_param("roleArn")
        channel = self.medialive_backend.update_channel(
            channel_id=channel_id,
            cdi_input_specification=cdi_input_specification,
            destinations=destinations,
            encoder_settings=encoder_settings,
            input_attachments=input_attachments,
            input_specification=input_specification,
            log_level=log_level,
            name=name,
            role_arn=role_arn,
        )
        return json.dumps(dict(channel=channel.to_dict()))

    def create_input(self):
        destinations = self._get_param("destinations")
        input_devices = self._get_param("inputDevices")
        input_security_groups = self._get_param("inputSecurityGroups")
        media_connect_flows = self._get_param("mediaConnectFlows")
        name = self._get_param("name")
        request_id = self._get_param("requestId")
        role_arn = self._get_param("roleArn")
        sources = self._get_param("sources")
        tags = self._get_param("tags")
        type = self._get_param("type")
        vpc = self._get_param("vpc")
        a_input = self.medialive_backend.create_input(
            destinations=destinations,
            input_devices=input_devices,
            input_security_groups=input_security_groups,
            media_connect_flows=media_connect_flows,
            name=name,
            request_id=request_id,
            role_arn=role_arn,
            sources=sources,
            tags=tags,
            type=type,
            vpc=vpc,
        )
        return json.dumps({"input": a_input.to_dict()})

    def describe_input(self):
        input_id = self._get_param("inputId")
        return json.dumps(self.medialive_backend.describe_input(input_id=input_id,))

    def list_inputs(self):
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        inputs, next_token = self.medialive_backend.list_inputs(
            max_results=max_results, next_token=next_token,
        )

        return json.dumps(dict(inputs=inputs, nextToken=next_token))

    def delete_input(self):
        input_id = self._get_param("inputId")
        self.medialive_backend.delete_input(input_id=input_id,)
        return json.dumps({})

    def update_input(self):
        destinations = self._get_param("destinations")
        input_devices = self._get_param("inputDevices")
        input_id = self._get_param("inputId")
        input_security_groups = self._get_param("inputSecurityGroups")
        media_connect_flows = self._get_param("mediaConnectFlows")
        name = self._get_param("name")
        role_arn = self._get_param("roleArn")
        sources = self._get_param("sources")
        a_input = self.medialive_backend.update_input(
            destinations=destinations,
            input_devices=input_devices,
            input_id=input_id,
            input_security_groups=input_security_groups,
            media_connect_flows=media_connect_flows,
            name=name,
            role_arn=role_arn,
            sources=sources,
        )
        return json.dumps(dict(input=a_input.to_dict()))
