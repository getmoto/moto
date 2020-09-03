from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from moto.kinesisvideo import kinesisvideo_backends
from moto.sts.utils import random_session_token


class KinesisVideoArchivedMediaBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(KinesisVideoArchivedMediaBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

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
        stream = kinesisvideo_backends[self.region_name]._get_stream(
            stream_name, stream_arn
        )
        api_name = "GET_HLS_STREAMING_SESSION_URL"
        data_endpoint = stream.get_data_endpoint(api_name)
        session_token = random_session_token()
        hls_url = "{}/hls/v1/getHLSMasterPlaylist.m3u8?SessionToken={}".format(
            data_endpoint, session_token
        )
        return hls_url


kinesisvideoarchivedmedia_backends = {}
for region in Session().get_available_regions("kinesis-video-archived-media"):
    kinesisvideoarchivedmedia_backends[region] = KinesisVideoArchivedMediaBackend(
        region
    )
for region in Session().get_available_regions(
    "kinesis-video-archived-media", partition_name="aws-us-gov"
):
    kinesisvideoarchivedmedia_backends[region] = KinesisVideoArchivedMediaBackend(
        region
    )
for region in Session().get_available_regions(
    "kinesis-video-archived-media", partition_name="aws-cn"
):
    kinesisvideoarchivedmedia_backends[region] = KinesisVideoArchivedMediaBackend(
        region
    )
