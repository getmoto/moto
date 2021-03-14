from __future__ import unicode_literals
from boto3 import Session
from moto.core import BaseBackend, BaseModel
from datetime import datetime
from uuid import uuid4
from .exceptions import MissingParameterError


class GuardDutyBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(GuardDutyBackend, self).__init__()
        self.region_name = region_name
        self.detectors = {}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def create_detector(
        self, enable, client_token, finding_publishing_frequency, data_sources, tags
    ):
        if finding_publishing_frequency not in [
            "FIFTEEN_MINUTES",
            "ONE_HOUR",
            "SIX_HOURS",
        ]:
            finding_publishing_frequency = "SIX_HOURS"

        if enable is None or "":
            raise MissingParameterError(parameter="enabled")

        service_role = "AWSServiceRoleForAmazonGuardDuty"
        print(finding_publishing_frequency)
        detector = Detector(
            self,
            datetime.now,
            finding_publishing_frequency,
            service_role,
            enable,
            data_sources,
            tags,
        )
        self.detectors[detector.id] = detector
        return detector.id

    def list_detectors(self, maxResults, nextToken):
        detectorids = []
        for detector in self.detectors:
            detectorids.append(self.detectors[detector].id)
            nextToken = str(maxResults) if len(detectorids) > maxResults else None
            return detectorids, nextToken


class Detector(BaseModel):
    def __init__(
        self,
        created_at,
        finding_publish_freq,
        service_role,
        status,
        updated_at,
        datasources,
        tags,
    ):
        self.id = str(uuid4())
        self.created_at = created_at
        self.finding_publish_freq = finding_publish_freq
        self.service_role = service_role
        self.status = status
        self.updated_at = updated_at
        self.datasources = datasources
        self.tags = tags


guardduty_backends = {}
for region in Session().get_available_regions("guardduty"):
    guardduty_backends[region] = GuardDutyBackend()
for region in Session().get_available_regions("guardduty", partition_name="aws-us-gov"):
    guardduty_backends[region] = GuardDutyBackend()
for region in Session().get_available_regions("guardduty", partition_name="aws-cn"):
    guardduty_backends[region] = GuardDutyBackend()
