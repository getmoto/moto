from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel


class Stream(BaseModel):
    def __init__(
        self,
        region_name,
        device_name,
        stream_name,
        media_type,
        kms_key_id,
        data_retention_in_hours,
        tags,
    ):
        self.region_name = region_name
        self.stream_name = stream_name
        self.device_name = device_name
        self.media_type = media_type
        self.kms_key_id = kms_key_id
        self.data_retention_in_hours = data_retention_in_hours
        self.tags = tags
        stream_arn = "arn:aws:kinesisvideo:{}:123456789012:stream/{}/1598784211076".format(
            self.region_name, self.stream_name
        )
        self.arn = stream_arn


class KinesisVideoBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(KinesisVideoBackend, self).__init__()
        self.region_name = region_name
        self.streams = []

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_stream(
        self,
        device_name,
        stream_name,
        media_type,
        kms_key_id,
        data_retention_in_hours,
        tags,
    ):
        # implement here
        stream = Stream(
            self.region_name,
            device_name,
            stream_name,
            media_type,
            kms_key_id,
            data_retention_in_hours,
            tags,
        )
        self.streams.append(stream)
        return stream.arn

    # add methods from here


kinesisvideo_backends = {}
for region in Session().get_available_regions("kinesisvideo"):
    kinesisvideo_backends[region] = KinesisVideoBackend()
for region in Session().get_available_regions(
    "kinesisvideo", partition_name="aws-us-gov"
):
    kinesisvideo_backends[region] = KinesisVideoBackend()
for region in Session().get_available_regions("kinesisvideo", partition_name="aws-cn"):
    kinesisvideo_backends[region] = KinesisVideoBackend()
