from moto.core import BaseBackend
from moto.core.utils import BackendDict
from moto.kinesisvideo import kinesisvideo_backends
from moto.sts.utils import random_session_token


class KinesisVideoArchivedMediaBackend(BaseBackend):
    def __init__(self, region_name=None):
        super().__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def _get_streaming_url(self, stream_name, stream_arn, api_name):
        stream = kinesisvideo_backends[self.region_name]._get_stream(
            stream_name, stream_arn
        )
        data_endpoint = stream.get_data_endpoint(api_name)
        session_token = random_session_token()
        api_to_relative_path = {
            "GET_HLS_STREAMING_SESSION_URL": "/hls/v1/getHLSMasterPlaylist.m3u8",
            "GET_DASH_STREAMING_SESSION_URL": "/dash/v1/getDASHManifest.mpd",
        }
        relative_path = api_to_relative_path[api_name]
        url = "{}{}?SessionToken={}".format(data_endpoint, relative_path, session_token)
        return url

    def get_hls_streaming_session_url(
        self,
        stream_name,
        stream_arn,
        playback_mode,
        hls_fragment_selector,
        container_format,
        discontinuity_mode,
        display_fragment_timestamp,
        expires,
        max_media_playlist_fragment_results,
    ):
        # Ignore option paramters as the format of hls_url does't depends on them
        api_name = "GET_HLS_STREAMING_SESSION_URL"
        url = self._get_streaming_url(stream_name, stream_arn, api_name)
        return url

    def get_dash_streaming_session_url(
        self,
        stream_name,
        stream_arn,
        playback_mode,
        display_fragment_timestamp,
        display_fragment_number,
        dash_fragment_selector,
        expires,
        max_manifest_fragment_results,
    ):
        # Ignore option paramters as the format of hls_url does't depends on them
        api_name = "GET_DASH_STREAMING_SESSION_URL"
        url = self._get_streaming_url(stream_name, stream_arn, api_name)
        return url

    def get_clip(self, stream_name, stream_arn, clip_fragment_selector):
        kinesisvideo_backends[self.region_name]._get_stream(stream_name, stream_arn)
        content_type = "video/mp4"  # Fixed content_type as it depends on input stream
        payload = b"sample-mp4-video"
        return content_type, payload


kinesisvideoarchivedmedia_backends = BackendDict(
    KinesisVideoArchivedMediaBackend, "kinesis-video-archived-media"
)
