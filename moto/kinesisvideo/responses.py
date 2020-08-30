from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import kinesisvideo_backends
import json


class KinesisVideoResponse(BaseResponse):
    SERVICE_NAME = "kinesisvideo"

    @property
    def kinesisvideo_backend(self):
        return kinesisvideo_backends[self.region]

    def create_stream(self):
        device_name = self._get_param("DeviceName")
        stream_name = self._get_param("StreamName")
        media_type = self._get_param("MediaType")
        kms_key_id = self._get_param("KmsKeyId")
        data_retention_in_hours = self._get_int_param("DataRetentionInHours")
        tags = self._get_param("Tags")
        stream_arn = self.kinesisvideo_backend.create_stream(
            device_name=device_name,
            stream_name=stream_name,
            media_type=media_type,
            kms_key_id=kms_key_id,
            data_retention_in_hours=data_retention_in_hours,
            tags=tags,
        )
        return json.dumps(dict(StreamARN=stream_arn))

    def describe_stream(self):
        stream_name = self._get_param("StreamName")
        stream_arn = self._get_param("StreamARN")
        stream_info = self.kinesisvideo_backend.describe_stream(
            stream_name=stream_name, stream_arn=stream_arn,
        )
        return json.dumps(dict(StreamInfo=stream_info))

    # add methods from here


# add templates from here
