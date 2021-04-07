from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from collections import OrderedDict


class Channel(BaseModel):
    def __init__(self, *args, **kwargs):
        self.arn = kwargs.get("arn")
        self.channel_id = kwargs.get("channel_id")
        self.description = kwargs.get("description")
        self.tags = kwargs.get("tags")

    def to_dict(self, exclude=None):
        data = {
            "arn": self.arn,
            "id": self.channel_id,
            "description": self.description,
            "tags": self.tags,
        }
        if exclude:
            for key in exclude:
                del data[key]
        return data


class OriginEndpoint(BaseModel):
    def __init__(self, *args, **kwargs):
        self.arn = kwargs.get("arn")
        self.authorization = kwargs.get("authorization")
        self.channel_id = kwargs.get("channel_id")
        self.cmaf_package = kwargs.get("cmaf_package")
        self.dash_package = kwargs.get("dash_package")
        self.description = kwargs.get("description")
        self.hls_package = kwargs.get("hls_package")
        self.id = kwargs.get("id")
        self.manifest_name = kwargs.get("manifest_name")
        self.mss_package = kwargs.get("mss_package")
        self.origination = kwargs.get("origination")
        self.startover_window_seconds = kwargs.get("startover_window_seconds")
        self.tags = kwargs.get("tags")
        self.time_delay_seconds = kwargs.get("time_delay_seconds")
        self.url = kwargs.get("url")
        self.whitelist = kwargs.get("whitelist")

    def to_dict(self):
        data = {
            "arn": self.arn,
            "authorization": self.authorization,
            "channelId": self.channel_id,
            "cmafPackage": self.cmaf_package,
            "dashPackage": self.dash_package,
            "description": self.description,
            "hlsPackage": self.hls_package,
            "id": self.id,
            "manifestName": self.manifest_name,
            "mssPackage": self.mss_package,
            "origination": self.origination,
            "startoverWindowSeconds": self.startover_window_seconds,
            "tags": self.tags,
            "timeDelaySeconds": self.time_delay_seconds,
            "url": self.url,
            "whitelist": self.whitelist,
        }
        return data


class MediaPackageBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(MediaPackageBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)
        self._channels = OrderedDict()
        self._origin_endpoints = OrderedDict()

    def create_channel(self, description, id, tags):
        arn = "arn:aws:mediapackage:channel:{}".format(id)
        channel = Channel(
            arn=arn,
            description=description,
            egress_access_logs={},
            hls_ingest={},
            channel_id=id,
            ingress_access_logs={},
            tags=tags,
        )
        self._channels[id] = channel
        return channel

    def list_channels(self):
        channels = list(self._channels.values())
        response_channels = [c.to_dict() for c in channels]
        return response_channels

    def describe_channel(self, id):
        channel = self._channels[id]
        return channel.to_dict()

    def delete_channel(self, id):
        channel = self._channels[id]
        del self._channels[id]
        return channel.to_dict()

    def create_origin_endpoint(
        self,
        authorization,
        channel_id,
        cmaf_package,
        dash_package,
        description,
        hls_package,
        id,
        manifest_name,
        mss_package,
        origination,
        startover_window_seconds,
        tags,
        time_delay_seconds,
        whitelist,
    ):
        arn = "arn:aws:mediapackage:origin_endpoint:{}".format(id)
        url = "https://origin-endpoint.mediapackage.{}.amazonaws.com/{}".format(
            self.region_name, id
        )
        origin_endpoint = OriginEndpoint(
            arn=arn,
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
            url=url,
            whitelist=whitelist,
        )
        self._origin_endpoints[id] = origin_endpoint
        return origin_endpoint

    def describe_origin_endpoint(self, id):
        origin_endpoint = self._origin_endpoints[id]
        return origin_endpoint.to_dict()

    def list_origin_endpoints(self):
        origin_endpoints = list(self._origin_endpoints.values())
        response_origin_endpoints = [o.to_dict() for o in origin_endpoints]
        return response_origin_endpoints

    def delete_origin_endpoint(self, id):
        origin_endpoint = self._origin_endpoints[id]
        del self._origin_endpoints[id]
        return origin_endpoint.to_dict()

    def update_origin_endpoint(
        self,
        authorization,
        cmaf_package,
        dash_package,
        description,
        hls_package,
        id,
        manifest_name,
        mss_package,
        origination,
        startover_window_seconds,
        time_delay_seconds,
        whitelist,
    ):
        origin_endpoint = self._origin_endpoints[id]
        origin_endpoint.authorization = authorization
        origin_endpoint.cmaf_package = cmaf_package
        origin_endpoint.dash_package = dash_package
        origin_endpoint.description = description
        origin_endpoint.hls_package = hls_package
        origin_endpoint.manifest_name = manifest_name
        origin_endpoint.mss_package = mss_package
        origin_endpoint.origination = origination
        origin_endpoint.startover_window_seconds = startover_window_seconds
        origin_endpoint.time_delay_seconds = time_delay_seconds
        origin_endpoint.whitelist = whitelist
        return origin_endpoint


mediapackage_backends = {}
for region in Session().get_available_regions("mediapackage"):
    mediapackage_backends[region] = MediaPackageBackend(region)
for region in Session().get_available_regions(
    "mediapackage", partition_name="aws-us-gov"
):
    mediapackage_backends[region] = MediaPackageBackend(region)
for region in Session().get_available_regions("mediapackage", partition_name="aws-cn"):
    mediapackage_backends[region] = MediaPackageBackend(region)
