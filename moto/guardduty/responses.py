from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import guardduty_backends
import json


class GuardDutyResponse(BaseResponse):
    SERVICE_NAME = "guardduty"

    @property
    def guardduty_backend(self):
        return guardduty_backends[self.region]

    # @property
    # def request_params(self):
    #     try:
    #         return json.loads(self.body)
    #     except ValueError:
    #         return {}

    # def _get_param(self, param, default=None):
    #     return self.request_params.get(param,default)

    def create_detector(self):
        enable = self._get_param("enable")
        client_token = self._get_param("clientToken")
        finding_publishing_frequency = self._get_param("findingPublishingFrequency")
        data_sources = self._get_param("dataSources")
        tags = self._get_param("tags")

        detector_id = self.guardduty_backend.create_detector(
            enable, client_token, finding_publishing_frequency, data_sources, tags
        )

        return json.dumps(dict(detectorId=detector_id))

    def list_detectors(self):
        maxResults = int(self._get_param("maxResults"))
        nextToken = self._get_param("nextToken")
        detectorIds, nextToken = self.guardduty_backend.list_detectors(
            maxResults, nextToken
        )

        return json.dumps({"DetectorIds": detectorIds, "NextToken": nextToken})

    # add methods from here


# add templates from here
