from moto.core import BaseBackend, BaseModel
from datetime import datetime
from .exceptions import ResourceNotFoundException, ResourceInUseException
import random
import string
from moto.core.utils import get_random_hex, BackendDict
from moto.core import get_account_id


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
        self.status = "ACTIVE"
        self.version = self._get_random_string()
        self.creation_time = datetime.utcnow()
        stream_arn = "arn:aws:kinesisvideo:{}:{}:stream/{}/1598784211076".format(
            self.region_name, get_account_id(), self.stream_name
        )
        self.data_endpoint_number = get_random_hex()
        self.arn = stream_arn

    def _get_random_string(self, length=20):
        letters = string.ascii_lowercase
        result_str = "".join([random.choice(letters) for _ in range(length)])
        return result_str

    def get_data_endpoint(self, api_name):
        data_endpoint_prefix = "s-" if api_name in ("PUT_MEDIA", "GET_MEDIA") else "b-"
        return "https://{}{}.kinesisvideo.{}.amazonaws.com".format(
            data_endpoint_prefix, self.data_endpoint_number, self.region_name
        )

    def to_dict(self):
        return {
            "DeviceName": self.device_name,
            "StreamName": self.stream_name,
            "StreamARN": self.arn,
            "MediaType": self.media_type,
            "KmsKeyId": self.kms_key_id,
            "Version": self.version,
            "Status": self.status,
            "CreationTime": self.creation_time.isoformat(),
            "DataRetentionInHours": self.data_retention_in_hours,
        }


class KinesisVideoBackend(BaseBackend):
    def __init__(self, region_name=None):
        super().__init__()
        self.region_name = region_name
        self.streams = {}

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
        streams = [_ for _ in self.streams.values() if _.stream_name == stream_name]
        if len(streams) > 0:
            raise ResourceInUseException(
                "The stream {} already exists.".format(stream_name)
            )
        stream = Stream(
            self.region_name,
            device_name,
            stream_name,
            media_type,
            kms_key_id,
            data_retention_in_hours,
            tags,
        )
        self.streams[stream.arn] = stream
        return stream.arn

    def _get_stream(self, stream_name, stream_arn):
        if stream_name:
            streams = [_ for _ in self.streams.values() if _.stream_name == stream_name]
            if len(streams) == 0:
                raise ResourceNotFoundException()
            stream = streams[0]
        elif stream_arn:
            stream = self.streams.get(stream_arn)
            if stream is None:
                raise ResourceNotFoundException()
        return stream

    def describe_stream(self, stream_name, stream_arn):
        stream = self._get_stream(stream_name, stream_arn)
        stream_info = stream.to_dict()
        return stream_info

    def list_streams(self):
        """
        Pagination and the StreamNameCondition-parameter are not yet implemented
        """
        stream_info_list = [_.to_dict() for _ in self.streams.values()]
        next_token = None
        return stream_info_list, next_token

    def delete_stream(self, stream_arn):
        """
        The CurrentVersion-parameter is not yet implemented
        """
        stream = self.streams.get(stream_arn)
        if stream is None:
            raise ResourceNotFoundException()
        del self.streams[stream_arn]

    def get_data_endpoint(self, stream_name, stream_arn, api_name):
        stream = self._get_stream(stream_name, stream_arn)
        return stream.get_data_endpoint(api_name)

    # add methods from here


kinesisvideo_backends = BackendDict(KinesisVideoBackend, "kinesisvideo")
