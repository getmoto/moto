from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import guardduty_backends
import json
from urllib.parse import unquote


class GuardDutyResponse(BaseResponse):
    SERVICE_NAME = "guardduty"

    @property
    def guardduty_backend(self):
        return guardduty_backends[self.region]

    def filter(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_filter()
        elif request.method == "DELETE":
            return self.delete_filter()
        elif request.method == "POST":
            return self.update_filter()

    def filters(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_filter()

    def detectors(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            return self.create_detector()
        elif request.method == "GET":
            return self.list_detectors()
        else:
            return 404, {}, ""

    def detector(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.get_detector()
        elif request.method == "DELETE":
            return self.delete_detector()
        elif request.method == "POST":
            return self.update_detector()

    def create_filter(self):
        detector_id = self.path.split("/")[-2]
        name = self._get_param("name")
        action = self._get_param("action")
        description = self._get_param("description")
        finding_criteria = self._get_param("findingCriteria")
        rank = self._get_param("rank")

        self.guardduty_backend.create_filter(
            detector_id, name, action, description, finding_criteria, rank
        )
        return 200, {}, json.dumps({"name": name})

    def create_detector(self):
        enable = self._get_param("enable")
        finding_publishing_frequency = self._get_param("findingPublishingFrequency")
        data_sources = self._get_param("dataSources")
        tags = self._get_param("tags")

        detector_id = self.guardduty_backend.create_detector(
            enable, finding_publishing_frequency, data_sources, tags
        )

        return 200, {}, json.dumps(dict(detectorId=detector_id))

    def delete_detector(self):
        detector_id = self.path.split("/")[-1]

        self.guardduty_backend.delete_detector(detector_id)
        return 200, {}, "{}"

    def delete_filter(self):
        detector_id = self.path.split("/")[-3]
        filter_name = unquote(self.path.split("/")[-1])

        self.guardduty_backend.delete_filter(detector_id, filter_name)
        return 200, {}, "{}"

    def enable_organization_admin_account(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        admin_account = self._get_param("adminAccountId")
        self.guardduty_backend.enable_organization_admin_account(admin_account)

        return 200, {}, "{}"

    def list_organization_admin_accounts(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)

        account_ids = self.guardduty_backend.list_organization_admin_accounts()

        return (
            200,
            {},
            json.dumps(
                {
                    "adminAccounts": [
                        {"adminAccountId": account_id, "adminStatus": "ENABLED"}
                        for account_id in account_ids
                    ]
                }
            ),
        )

    def list_detectors(self):
        detector_ids = self.guardduty_backend.list_detectors()

        return 200, {}, json.dumps({"detectorIds": detector_ids})

    def get_detector(self):
        detector_id = self.path.split("/")[-1]

        detector = self.guardduty_backend.get_detector(detector_id)
        return 200, {}, json.dumps(detector.to_json())

    def get_filter(self):
        detector_id = self.path.split("/")[-3]
        filter_name = unquote(self.path.split("/")[-1])

        _filter = self.guardduty_backend.get_filter(detector_id, filter_name)
        return 200, {}, json.dumps(_filter.to_json())

    def update_detector(self):
        detector_id = self.path.split("/")[-1]
        enable = self._get_param("enable")
        finding_publishing_frequency = self._get_param("findingPublishingFrequency")
        data_sources = self._get_param("dataSources")

        self.guardduty_backend.update_detector(
            detector_id, enable, finding_publishing_frequency, data_sources
        )
        return 200, {}, "{}"

    def update_filter(self):
        detector_id = self.path.split("/")[-3]
        filter_name = unquote(self.path.split("/")[-1])
        action = self._get_param("action")
        description = self._get_param("description")
        finding_criteria = self._get_param("findingCriteria")
        rank = self._get_param("rank")

        self.guardduty_backend.update_filter(
            detector_id,
            filter_name,
            action=action,
            description=description,
            finding_criteria=finding_criteria,
            rank=rank,
        )
        return 200, {}, json.dumps({"name": filter_name})
