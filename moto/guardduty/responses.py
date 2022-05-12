from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import guardduty_backends
import json


class GuardDutyResponse(BaseResponse):
    SERVICE_NAME = "guardduty"

    @property
    def guardduty_backend(self):
        return guardduty_backends[self.region]

    def detector(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_detector()
        elif request.method == "GET":
            return self.list_detectors()
        else:
            return 404, {}, ""

    def create_detector(self):
        enable = self._get_param("enable")
        finding_publishing_frequency = self._get_param("findingPublishingFrequency")
        data_sources = self._get_param("dataSources")
        tags = self._get_param("tags")

        detector_id = self.guardduty_backend.create_detector(
            enable, finding_publishing_frequency, data_sources, tags
        )

        return 200, {}, json.dumps(dict(detectorId=detector_id))

    def list_detectors(self):
        detector_ids = self.guardduty_backend.list_detectors()

        return 200, {}, json.dumps({"detectorIds": detector_ids})
