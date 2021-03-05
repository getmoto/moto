from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import mediapackage_backends
import json


class MediaPackageResponse(BaseResponse):
    SERVICE_NAME = 'mediapackage'
    @property
    def mediapackage_backend(self):
        return mediapackage_backends[self.region]

    
    def create_channel(self):
        description = self._get_param("description")
        id = self._get_param("id")
        tags = self._get_param("tags")
        channel = self.mediapackage_backend.create_channel(
            description=description,
            id=id,
            tags=tags,
        )
        return json.dumps(channel.to_dict())

    
    def describe_channel(self):
        id = self._get_param("id")
        return json.dumps(
            self.mediapackage_backend.describe_channel(id=id,)
        )
# add templates from here
    
    def create_origin_endpoint(self):
        authorization = self._get_param("authorization")
        channel_id = self._get_param("channel_id")
        cmaf_package = self._get_param("cmaf_package")
        dash_package = self._get_param("DashPackage")
        description = self._get_param("description")
        hls_package = self._get_param("hls_package")
        id = self._get_param("id")
        manifest_name = self._get_param("ManifestName")
        mss_package = self._get_param("MssPackage")
        origination = self._get_param("origination")
        startover_window_seconds = self._get_int_param("StartoverWindowSeconds")
        tags = self._get_param("Tags")
        time_delay_seconds = self._get_int_param("TimeDelaySeconds.member")
        whitelist = self._get_list_prefix("Whitelist.member")
        origin_endpoint = self.mediapackage_backend.create_origin_endpoint(
            authorization=authorization,
            channel_id=channel_id,
            cmaf_package=cmaf_package,
            dash_package=dash_package,
            description=description,
            hls_package=hls_package,
            id=id,
            manifest_name=manifest_name,
            mss_package=mss_package,
            origination=origination,
            startover_window_seconds=startover_window_seconds,
            tags=tags,
            time_delay_seconds=time_delay_seconds,
            whitelist=whitelist,
        )
        return json.dumps(origin_endpoint.to_dict())