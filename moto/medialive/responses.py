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
        # destinations = self._get_list_prefix("destinations.member")
        destinations = self._get_param("destinations")
        encoder_settings = self._get_param("encoderSettings")
        # input_attachments = self._get_list_prefix("inputAttachments.member")
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
        # TODO: adjust response
        return json.dumps(dict(channel=channel))

    # add methods from here


# add templates from here
