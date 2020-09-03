from __future__ import unicode_literals
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
        playback_mode = self._get_param("PlaybackMode")
        hls_fragment_selector = self._get_param("HLSFragmentSelector")
        container_format = self._get_param("ContainerFormat")
        discontinuity_mode = self._get_param("DiscontinuityMode")
        display_fragment_timestamp = self._get_param("DisplayFragmentTimestamp")
        expires = self._get_int_param("Expires")
        max_media_playlist_fragment_results = self._get_param(
            "MaxMediaPlaylistFragmentResults"
        )
        hls_streaming_session_url = self.kinesisvideoarchivedmedia_backend.get_hls_streaming_session_url(
            stream_name=stream_name,
            stream_arn=stream_arn,
            playback_mode=playback_mode,
            hls_fragment_selector=hls_fragment_selector,
            container_format=container_format,
            discontinuity_mode=discontinuity_mode,
            display_fragment_timestamp=display_fragment_timestamp,
            expires=expires,
            max_media_playlist_fragment_results=max_media_playlist_fragment_results,
        )
        return json.dumps(dict(HLSStreamingSessionURL=hls_streaming_session_url))

    # add methods from here


# add templates from here
