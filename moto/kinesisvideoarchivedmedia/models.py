from moto.core import BaseBackend
from moto.core.utils import BackendDict
from moto.kinesisvideo import kinesisvideo_backends
from moto.sts.utils import random_session_token


class KinesisVideoArchivedMediaBackend(BaseBackend):
    @property
    def backend(self):
        return kinesisvideo_backends[self.account_id][self.region_name]

    def _get_streaming_url(self, stream_name, stream_arn, api_name):
        stream = self.backend._get_stream(stream_name, stream_arn)
        data_endpoint = stream.get_data_endpoint(api_name)
        session_token = random_session_token()
        api_to_relative_path = {
            "GET_HLS_STREAMING_SESSION_URL": "/hls/v1/getHLSMasterPlaylist.m3u8",
            "GET_DASH_STREAMING_SESSION_URL": "/dash/v1/getDASHManifest.mpd",
        }
        relative_path = api_to_relative_path[api_name]
        url = "{}{}?SessionToken={}".format(data_endpoint, relative_path, session_token)
        return url

    def get_hls_streaming_session_url(self, stream_name, stream_arn):
        # Ignore option paramters as the format of hls_url does't depends on them
        api_name = "GET_HLS_STREAMING_SESSION_URL"
        url = self._get_streaming_url(stream_name, stream_arn, api_name)
        return url

    def get_dash_streaming_session_url(self, stream_name, stream_arn):
        # Ignore option paramters as the format of hls_url does't depends on them
        api_name = "GET_DASH_STREAMING_SESSION_URL"
        url = self._get_streaming_url(stream_name, stream_arn, api_name)
        return url

    def get_clip(self, stream_name, stream_arn):
        self.backend._get_stream(stream_name, stream_arn)
        content_type = "video/mp4"  # Fixed content_type as it depends on input stream
        payload = b"sample-mp4-video"
        return content_type, payload


kinesisvideoarchivedmedia_backends = BackendDict(
    KinesisVideoArchivedMediaBackend, "kinesis-video-archived-media"
)
