from moto.core import BaseBackend, BackendDict, BaseModel
from datetime import datetime
from .exceptions import ResourceNotFoundException, ResourceInUseException
from moto.moto_api._internal import mock_random as random


class Stream(BaseModel):
    def __init__(
        self,
        account_id,
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
        self.version = random.get_random_string(include_digits=False, lower_case=True)
        self.creation_time = datetime.utcnow()
        stream_arn = f"arn:aws:kinesisvideo:{region_name}:{account_id}:stream/{stream_name}/1598784211076"
        self.data_endpoint_number = random.get_random_hex()
        self.arn = stream_arn

    def get_data_endpoint(self, api_name):
        data_endpoint_prefix = "s-" if api_name in ("PUT_MEDIA", "GET_MEDIA") else "b-"
        return f"https://{data_endpoint_prefix}{self.data_endpoint_number}.kinesisvideo.{self.region_name}.amazonaws.com"

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
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.streams = {}

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
            raise ResourceInUseException(f"The stream {stream_name} already exists.")
        stream = Stream(
            self.account_id,
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
