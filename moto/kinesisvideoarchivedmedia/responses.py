from moto.core.responses import BaseResponse
from .models import kinesisvideoarchivedmedia_backends
import json


class KinesisVideoArchivedMediaResponse(BaseResponse):
    SERVICE_NAME = "kinesis-video-archived-media"

    @property
    def kinesisvideoarchivedmedia_backend(self):
        return kinesisvideoarchivedmedia_backends[self.region]

    def get_hls_streaming_session_url(self):
        stream_name = self._get_param("StreamName")
        stream_arn = self._get_param("StreamARN")
        hls_streaming_session_url = (
            self.kinesisvideoarchivedmedia_backend.get_hls_streaming_session_url(
                stream_name=stream_name, stream_arn=stream_arn
            )
        )
        return json.dumps(dict(HLSStreamingSessionURL=hls_streaming_session_url))

    def get_dash_streaming_session_url(self):
        stream_name = self._get_param("StreamName")
        stream_arn = self._get_param("StreamARN")
        dash_streaming_session_url = (
            self.kinesisvideoarchivedmedia_backend.get_dash_streaming_session_url(
                stream_name=stream_name, stream_arn=stream_arn
            )
        )
        return json.dumps(dict(DASHStreamingSessionURL=dash_streaming_session_url))

    def get_clip(self):
        stream_name = self._get_param("StreamName")
        stream_arn = self._get_param("StreamARN")
        content_type, payload = self.kinesisvideoarchivedmedia_backend.get_clip(
            stream_name=stream_name, stream_arn=stream_arn
        )
        new_headers = {"Content-Type": content_type}
        return payload, new_headers
