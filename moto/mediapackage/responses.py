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
        description = self._get_param("Description")
        id = self._get_param("Id")
        tags = self._get_param("Tags")
        arn, description, egress_access_logs, hls_ingest, id, ingress_access_logs, tags = self.mediapackage_backend.create_channel(
            description=description,
            id=id,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(arn=arn, description=description, egressAccessLogs=egress_access_logs, hlsIngest=hls_ingest, id=id, ingressAccessLogs=ingress_access_logs, tags=tags))
    # add methods from here
    
    def describe_channel(self):
        id = self._get_param("Id")
        arn, description, egress_access_logs, hls_ingest, id, ingress_access_logs, tags = self.mediapackage_backend.describe_channel(
            id=id,
        )
        # TODO: adjust response
        return json.dumps(dict(arn=arn, description=description, egressAccessLogs=egress_access_logs, hlsIngest=hls_ingest, id=id, ingressAccessLogs=ingress_access_logs, tags=tags))


# add templates from here
