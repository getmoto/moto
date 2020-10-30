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
        cdi_input_specification = self._get_param("CdiInputSpecification")
        channel_class = self._get_param("ChannelClass")
        destinations = self._get_list_prefix("Destinations.member")
        encoder_settings = self._get_param("EncoderSettings")
        input_attachments = self._get_list_prefix("InputAttachments.member")
        input_specification = self._get_param("InputSpecification")
        log_level = self._get_param("LogLevel")
        name = self._get_param("Name")
        request_id = self._get_param("RequestId")
        reserved = self._get_param("Reserved")
        role_arn = self._get_param("RoleArn")
        tags = self._get_param("Tags")
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
        # TODO: adjust response
        return json.dumps(dict(channel=channel))

    # add methods from here


# add templates from here
