from datetime import datetime
from typing import Any

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random
from moto.utilities.utils import get_partition

from .exceptions import (
    DetectorNotFoundException,
    FilterNotFoundException,
    IPSetNotFoundException,
)


class GuardDutyBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.admin_account_ids: list[str] = []
        self.detectors: dict[str, Detector] = {}
        self.admin_accounts: dict[
            str, Detector
        ] = {}  # Store admin accounts by detector_id

    def create_detector(
        self,
        enable: bool,
        finding_publishing_frequency: str,
        data_sources: dict[str, Any],
        tags: dict[str, str],
        features: list[dict[str, Any]],
    ) -> str:
        if finding_publishing_frequency not in [
            "FIFTEEN_MINUTES",
            "ONE_HOUR",
            "SIX_HOURS",
        ]:
            finding_publishing_frequency = "SIX_HOURS"

        detector = Detector(
            account_id=self.account_id,
            region_name=self.region_name,
            created_at=datetime.now(),
            finding_publish_freq=finding_publishing_frequency,
            enabled=enable,
            datasources=data_sources,
            tags=tags,
            features=features,
        )
        self.detectors[detector.id] = detector
        return detector.id

    def create_filter(
        self,
        detector_id: str,
        name: str,
        action: str,
        description: str,
        finding_criteria: dict[str, Any],
        rank: int,
    ) -> None:
        detector = self.get_detector(detector_id)
        _filter = Filter(name, action, description, finding_criteria, rank)
        detector.add_filter(_filter)

    def create_ip_set(
        self,
        detector_id: str,
        name: str,
        ip_set_format: str,
        location: str,
        activate: bool,
        tags: dict[str, str],
        expected_bucket_owner: str | None,
    ) -> str:
        detector = self.get_detector(detector_id)
        ip_set = IPSet(
            name=name,
            ip_set_format=ip_set_format,
            location=location,
            activate=activate,
            tags=tags,
            expected_bucket_owner=expected_bucket_owner,
        )
        detector.add_ip_set(ip_set)
        return ip_set.id

    def delete_detector(self, detector_id: str) -> None:
        self.detectors.pop(detector_id, None)

    def delete_filter(self, detector_id: str, filter_name: str) -> None:
        detector = self.get_detector(detector_id)
        detector.delete_filter(filter_name)

    def delete_ip_set(self, detector_id: str, ip_set_id: str) -> None:
        detector = self.get_detector(detector_id)
        detector.delete_ip_set(ip_set_id)

    def enable_organization_admin_account(self, admin_account_id: str) -> None:
        self.admin_account_ids.append(admin_account_id)

    def list_organization_admin_accounts(self) -> list[str]:
        """
        Pagination is not yet implemented
        """
        return self.admin_account_ids

    def list_detectors(self) -> list[str]:
        """
        The MaxResults and NextToken-parameter have not yet been implemented.
        """
        detectorids = []
        for detector in self.detectors:
            detectorids.append(self.detectors[detector].id)
        return detectorids

    def list_ip_sets(self, detector_id: str) -> list[str]:
        """
        The MaxResults and NextToken-parameter have not yet been implemented.
        """
        detector = self.get_detector(detector_id)
        return list(detector.ip_sets.keys())

    def get_detector(self, detector_id: str) -> "Detector":
        if detector_id not in self.detectors:
            raise DetectorNotFoundException
        return self.detectors[detector_id]

    def get_administrator_account(self, detector_id: str) -> dict[str, Any]:
        """Get administrator account details."""
        self.get_detector(detector_id)

        if not self.admin_account_ids:
            return {}

        return {
            "Administrator": {
                "AccountId": self.admin_account_ids[0],
                "RelationshipStatus": "ENABLED",
            }
        }

    def get_filter(self, detector_id: str, filter_name: str) -> "Filter":
        detector = self.get_detector(detector_id)
        return detector.get_filter(filter_name)

    def get_ip_set(self, detector_id: str, ip_set_id: str) -> "IPSet":
        detector = self.get_detector(detector_id)
        return detector.get_ip_set(ip_set_id)

    def update_detector(
        self,
        detector_id: str,
        enable: bool,
        finding_publishing_frequency: str,
        data_sources: dict[str, Any],
        features: list[dict[str, Any]],
    ) -> None:
        detector = self.get_detector(detector_id)
        detector.update(enable, finding_publishing_frequency, data_sources, features)

    def update_filter(
        self,
        detector_id: str,
        filter_name: str,
        action: str,
        description: str,
        finding_criteria: dict[str, Any],
        rank: int,
    ) -> None:
        detector = self.get_detector(detector_id)
        detector.update_filter(
            filter_name,
            action=action,
            description=description,
            finding_criteria=finding_criteria,
            rank=rank,
        )

    def update_ip_set(
        self,
        detector_id: str,
        ip_set_id: str,
        name: str | None,
        location: str | None,
        activate: bool | None,
    ) -> None:
        detector = self.get_detector(detector_id)
        detector.update_ip_set(
            ip_set_id, name=name, location=location, activate=activate
        )


class Filter(BaseModel):
    def __init__(
        self,
        name: str,
        action: str,
        description: str,
        finding_criteria: dict[str, Any],
        rank: int,
    ):
        self.name = name
        self.action = action
        self.description = description
        self.finding_criteria = finding_criteria
        self.rank = rank or 1

    def update(
        self,
        action: str | None,
        description: str | None,
        finding_criteria: dict[str, Any] | None,
        rank: int | None,
    ) -> None:
        if action is not None:
            self.action = action
        if description is not None:
            self.description = description
        if finding_criteria is not None:
            self.finding_criteria = finding_criteria
        if rank is not None:
            self.rank = rank

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "action": self.action,
            "description": self.description,
            "findingCriteria": self.finding_criteria,
            "rank": self.rank,
        }


class IPSet(BaseModel):
    def __init__(
        self,
        name: str,
        ip_set_format: str,
        location: str,
        activate: bool,
        tags: dict[str, str],
        expected_bucket_owner: str | None,
    ):
        self.id = mock_random.get_random_hex(length=32)
        self.name = name
        self.format = ip_set_format
        self.location = location
        self.status = "ACTIVE" if activate else "INACTIVE"
        self.tags = tags or {}
        self.expected_bucket_owner = expected_bucket_owner

    def update(
        self,
        name: str | None,
        location: str | None,
        activate: bool | None,
    ) -> None:
        if name is not None:
            self.name = name
        if location is not None:
            self.location = location
        if activate is not None:
            self.status = "ACTIVE" if activate else "INACTIVE"

    def to_json(self) -> dict[str, Any]:
        resp = {
            "name": self.name,
            "format": self.format,
            "location": self.location,
            "status": self.status,
            "tags": self.tags,
        }
        if self.expected_bucket_owner:
            resp["expectedBucketOwner"] = self.expected_bucket_owner
        return resp


class Detector(BaseModel):
    def __init__(
        self,
        account_id: str,
        region_name: str,
        created_at: datetime,
        finding_publish_freq: str,
        enabled: bool,
        datasources: dict[str, Any],
        tags: dict[str, str],
        features: list[dict[str, Any]],
    ):
        self.id = mock_random.get_random_hex(length=32)
        self.created_at = created_at
        self.finding_publish_freq = finding_publish_freq
        self.service_role = f"arn:{get_partition(region_name)}:iam::{account_id}:role/aws-service-role/guardduty.amazonaws.com/AWSServiceRoleForAmazonGuardDuty"
        self.enabled = enabled
        self.updated_at = created_at
        self.datasources = datasources or {}
        self.tags = tags or {}
        # TODO: Implement feature configuration object and validation
        # https://docs.aws.amazon.com/guardduty/latest/APIReference/API_DetectorFeatureConfiguration.html
        self.features = features or []

        self.filters: dict[str, Filter] = {}
        self.ip_sets: dict[str, IPSet] = {}

    def add_filter(self, _filter: Filter) -> None:
        self.filters[_filter.name] = _filter

    def add_ip_set(self, ip_set: IPSet) -> None:
        self.ip_sets[ip_set.id] = ip_set

    def delete_ip_set(self, ip_set_id: str) -> None:
        self.ip_sets.pop(ip_set_id, None)

    def get_ip_set(self, ip_set_id: str) -> IPSet:
        if ip_set_id not in self.ip_sets:
            raise IPSetNotFoundException
        return self.ip_sets[ip_set_id]

    def update_ip_set(
        self,
        ip_set_id: str,
        name: str | None,
        location: str | None,
        activate: bool | None,
    ) -> None:
        ip_set = self.get_ip_set(ip_set_id)
        ip_set.update(name=name, location=location, activate=activate)

    def delete_filter(self, filter_name: str) -> None:
        self.filters.pop(filter_name, None)

    def get_filter(self, filter_name: str) -> Filter:
        if filter_name not in self.filters:
            raise FilterNotFoundException
        return self.filters[filter_name]

    def update_filter(
        self,
        filter_name: str,
        action: str,
        description: str,
        finding_criteria: dict[str, Any],
        rank: int,
    ) -> None:
        _filter = self.get_filter(filter_name)
        _filter.update(
            action=action,
            description=description,
            finding_criteria=finding_criteria,
            rank=rank,
        )

    def update(
        self,
        enable: bool,
        finding_publishing_frequency: str,
        data_sources: dict[str, Any],
        features: list[dict[str, Any]],
    ) -> None:
        if enable is not None:
            self.enabled = enable
        if finding_publishing_frequency is not None:
            self.finding_publish_freq = finding_publishing_frequency
        if data_sources is not None:
            self.datasources = data_sources
        if features is not None:
            self.features = features

    def to_json(self) -> dict[str, Any]:
        data_sources = {
            "cloudTrail": {"status": "DISABLED"},
            "dnsLogs": {"status": "DISABLED"},
            "flowLogs": {"status": "DISABLED"},
            "s3Logs": {
                "status": "ENABLED"
                if (self.datasources.get("s3Logs") or {}).get("enable")
                else "DISABLED"
            },
            "kubernetes": {
                "auditLogs": {
                    "status": "ENABLED"
                    if self.datasources.get("kubernetes", {})
                    .get("auditLogs", {})
                    .get("enable")
                    else "DISABLED"
                }
            },
        }
        return {
            "createdAt": self.created_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "findingPublishingFrequency": self.finding_publish_freq,
            "serviceRole": self.service_role,
            "status": "ENABLED" if self.enabled else "DISABLED",
            "updatedAt": self.updated_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "dataSources": data_sources,
            "tags": self.tags,
            "features": self.features,
        }


guardduty_backends = BackendDict(GuardDutyBackend, "guardduty")
