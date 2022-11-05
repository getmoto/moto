from moto.core.responses import BaseResponse
from .models import mediapackage_backends
import json


class MediaPackageResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="mediapackage")

    @property
    def mediapackage_backend(self):
        return mediapackage_backends[self.current_account][self.region]

    def create_channel(self):
        description = self._get_param("description")
        channel_id = self._get_param("id")
        tags = self._get_param("tags")
        channel = self.mediapackage_backend.create_channel(
            description=description, channel_id=channel_id, tags=tags
        )
        return json.dumps(channel.to_dict())

    def list_channels(self):
        channels = self.mediapackage_backend.list_channels()
        return json.dumps(dict(channels=channels))

    def describe_channel(self):
        channel_id = self._get_param("id")
        return json.dumps(
            self.mediapackage_backend.describe_channel(channel_id=channel_id)
        )

    def delete_channel(self):
        channel_id = self._get_param("id")
        return json.dumps(
            self.mediapackage_backend.delete_channel(channel_id=channel_id)
        )

    def create_origin_endpoint(self):
        authorization = self._get_param("authorization")
        channel_id = self._get_param("channelId")
        cmaf_package = self._get_param("cmafPackage")
        dash_package = self._get_param("dashPackage")
        description = self._get_param("description")
        hls_package = self._get_param("hlsPackage")
        endpoint_id = self._get_param("id")
        manifest_name = self._get_param("manifestName")
        mss_package = self._get_param("mssPackage")
        origination = self._get_param("origination")
        startover_window_seconds = self._get_int_param("startoverWindowSeconds")
        tags = self._get_param("tags")
        time_delay_seconds = self._get_int_param("timeDelaySeconds.member")
        whitelist = self._get_list_prefix("whitelist.member")
        origin_endpoint = self.mediapackage_backend.create_origin_endpoint(
            authorization=authorization,
            channel_id=channel_id,
            cmaf_package=cmaf_package,
            dash_package=dash_package,
            description=description,
            hls_package=hls_package,
            endpoint_id=endpoint_id,
            manifest_name=manifest_name,
            mss_package=mss_package,
            origination=origination,
            startover_window_seconds=startover_window_seconds,
            tags=tags,
            time_delay_seconds=time_delay_seconds,
            whitelist=whitelist,
        )
        return json.dumps(origin_endpoint.to_dict())

    def list_origin_endpoints(self):
        origin_endpoints = self.mediapackage_backend.list_origin_endpoints()
        return json.dumps(dict(originEndpoints=origin_endpoints))

    def describe_origin_endpoint(self):
        endpoint_id = self._get_param("id")
        return json.dumps(
            self.mediapackage_backend.describe_origin_endpoint(endpoint_id=endpoint_id)
        )

    def delete_origin_endpoint(self):
        endpoint_id = self._get_param("id")
        return json.dumps(
            self.mediapackage_backend.delete_origin_endpoint(endpoint_id=endpoint_id)
        )

    def update_origin_endpoint(self):
        authorization = self._get_param("authorization")
        cmaf_package = self._get_param("cmafPackage")
        dash_package = self._get_param("dashPackage")
        description = self._get_param("description")
        hls_package = self._get_param("hlsPackage")
        endpoint_id = self._get_param("id")
        manifest_name = self._get_param("manifestName")
        mss_package = self._get_param("mssPackage")
        origination = self._get_param("origination")
        startover_window_seconds = self._get_int_param("startoverWindowSeconds")
        time_delay_seconds = self._get_int_param("timeDelaySeconds")
        whitelist = self._get_list_prefix("whitelist.member")
        origin_endpoint = self.mediapackage_backend.update_origin_endpoint(
            authorization=authorization,
            cmaf_package=cmaf_package,
            dash_package=dash_package,
            description=description,
            hls_package=hls_package,
            endpoint_id=endpoint_id,
            manifest_name=manifest_name,
            mss_package=mss_package,
            origination=origination,
            startover_window_seconds=startover_window_seconds,
            time_delay_seconds=time_delay_seconds,
            whitelist=whitelist,
        )
        return json.dumps(origin_endpoint.to_dict())
