"""ShieldBackend class with methods for supported APIs."""

import random
import string
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random
from moto.shield.exceptions import (
    InvalidParameterException,
    InvalidResourceException,
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ValidationException,
)
from moto.utilities.arns import parse_arn
from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import PARTITION_NAMES


@dataclass
class Limit:
    type: str
    max: int

    def to_dict(self) -> dict[str, Any]:  # type: ignore
        return {"Type": self.type, "Max": self.max}


@dataclass
class ArbitraryPatternLimits:
    max_members: int

    def to_dict(self) -> dict[str, Any]:  # type: ignore
        return {"MaxMembers": self.max_members}


@dataclass
class PatternTypeLimits:
    arbitrary_pattern_limits: ArbitraryPatternLimits

    def to_dict(self) -> dict[str, Any]:  # type: ignore
        return {"ArbitraryPatternLimits": self.arbitrary_pattern_limits.to_dict()}


@dataclass
class ProtectionGroupLimits:
    max_protection_groups: int
    pattern_type_limits: PatternTypeLimits

    def to_dict(self) -> dict[str, Any]:  # type: ignore
        return {
            "MaxProtectionGroups": self.max_protection_groups,
            "PatternTypeLimits": self.pattern_type_limits.to_dict(),
        }


@dataclass
class ProtectionLimits:
    protected_resource_type_limits: list[Limit]

    def to_dict(self) -> dict[str, Any]:  # type: ignore
        return {
            "ProtectedResourceTypeLimits": [
                limit.to_dict() for limit in self.protected_resource_type_limits
            ]
        }


@dataclass
class SubscriptionLimits:
    protection_limits: ProtectionLimits
    protection_group_limits: ProtectionGroupLimits

    def to_dict(self) -> dict[str, Any]:  # type: ignore
        return {
            "ProtectionLimits": self.protection_limits.to_dict(),
            "ProtectionGroupLimits": self.protection_group_limits.to_dict(),
        }


def default_subscription_limits() -> SubscriptionLimits:
    protection_limits = ProtectionLimits(
        protected_resource_type_limits=[
            Limit(type="ELASTIC_IP_ADDRESS", max=100),
            Limit(type="APPLICATION_LOAD_BALANCER", max=50),
        ]
    )
    protection_group_limits = ProtectionGroupLimits(
        max_protection_groups=20,
        pattern_type_limits=PatternTypeLimits(
            arbitrary_pattern_limits=ArbitraryPatternLimits(max_members=100)
        ),
    )
    return SubscriptionLimits(
        protection_limits=protection_limits,
        protection_group_limits=protection_group_limits,
    )


@dataclass
class Subscription:
    account_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = field(
        default_factory=lambda: datetime.now() + timedelta(days=365)
    )
    auto_renew: str = field(default="ENABLED")
    limits: list[Limit] = field(
        default_factory=lambda: [Limit(type="MitigationCapacityUnits", max=10000)]
    )
    proactive_engagement_status: str = field(default="ENABLED")
    subscription_limits: SubscriptionLimits = field(
        default_factory=default_subscription_limits
    )
    subscription_arn: str = field(default="")
    time_commitment_in_seconds: int = field(default=31536000)

    def __post_init__(self) -> None:
        if self.subscription_arn == "":
            subscription_id = "".join(random.choices(string.hexdigits[:16], k=12))
            subscription_id_formatted = "-".join(
                [subscription_id[i : i + 4] for i in range(0, 12, 4)]
            )
            self.subscription_arn = f"arn:aws:shield::{self.account_id}:subscription/{subscription_id_formatted}"
        return

    def to_dict(self) -> dict[str, Any]:  # type: ignore
        return {
            "StartTime": self.start_time.strftime("%d/%m/%Y, %H:%M:%S"),
            "EndTime": self.end_time.strftime("%d/%m/%Y, %H:%M:%S"),
            "TimeCommitmentInSeconds": self.time_commitment_in_seconds,
            "AutoRenew": self.auto_renew,
            "Limits": [limit.to_dict() for limit in self.limits],
            "ProactiveEngagementStatus": self.proactive_engagement_status,
            "SubscriptionLimits": self.subscription_limits.to_dict(),
            "SubscriptionArn": self.subscription_arn,
        }


class Protection(BaseModel):
    def __init__(
        self, account_id: str, name: str, resource_arn: str, tags: list[dict[str, str]]
    ):
        self.name = name
        self.resource_arn = resource_arn
        self.protection_id = str(mock_random.uuid4())
        # value is returned in associate_health_check method.
        self.health_check_ids: list[str] = []
        # value is returned in enable_application_layer_automatic_response and disable_application_layer_automatic_response methods.
        self.application_layer_automatic_response_configuration: dict[str, Any] = {}
        self.protection_arn = (
            f"arn:aws:shield::{account_id}:protection/{self.protection_id}"
        )

        resource_types = {
            "cloudfront": "CLOUDFRONT_DISTRIBUTION",
            "globalaccelerator": "GLOBAL_ACCELERATOR",
            "route53": "ROUTE_53_HOSTED_ZONE",
            "ec2": "ELASTIC_IP_ALLOCATION",
        }
        res_type = resource_arn.split(":")[2]
        if res_type == "elasticloadbalancing":
            if resource_arn.split(":")[-1].split("/")[1] == "app":
                self.resource_type = "APPLICATION_LOAD_BALANCER"
            else:
                self.resource_type = "CLASSIC_LOAD_BALANCER"
        else:
            self.resource_type = resource_types[res_type]

    def to_dict(self) -> dict[str, Any]:
        dct = {
            "Id": self.protection_id,
            "Name": self.name,
            "ResourceArn": self.resource_arn,
            "HealthCheckIds": self.health_check_ids,
            "ProtectionArn": self.protection_arn,
            "ApplicationLayerAutomaticResponseConfiguration": self.application_layer_automatic_response_configuration,
        }
        return {k: v for k, v in dct.items() if v}


class ProtectionGroup(BaseModel):
    def __init__(
        self,
        account_id: str,
        protection_group_id: str,
        aggregation: str,
        pattern: str,
        resource_type: str | None,
        members: list[str] | None,
    ):
        self.protection_group_id = protection_group_id
        self.aggregation = aggregation
        self.pattern = pattern
        self.resource_type = resource_type
        self.members = members or []
        self.protection_group_arn = (
            f"arn:aws:shield::{account_id}:protection-group/{protection_group_id}"
        )

    def update(
        self,
        aggregation: str,
        pattern: str,
        resource_type: str | None,
        members: list[str] | None,
    ) -> None:
        # UpdateProtectionGroup requires Aggregation and Pattern, so the whole
        # definition is replaced rather than patched field by field.
        self.aggregation = aggregation
        self.pattern = pattern
        self.resource_type = resource_type
        self.members = members or []

    def to_dict(self) -> dict[str, Any]:
        dct: dict[str, Any] = {
            "ProtectionGroupId": self.protection_group_id,
            "Aggregation": self.aggregation,
            "Pattern": self.pattern,
            "Members": self.members,
            "ProtectionGroupArn": self.protection_group_arn,
        }
        if self.resource_type:
            dct["ResourceType"] = self.resource_type
        return dct


class ShieldBackend(BaseBackend):
    """Implementation of Shield APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.protections: dict[str, Protection] = {}
        self.protection_groups: dict[str, ProtectionGroup] = {}
        self.subscription: Subscription | None = None
        self.tagger = TaggingService()

    def validate_resource_arn(self, resource_arn: str) -> None:
        """Raise exception if the resource arn is invalid."""

        # Shield offers protection to only certain services.
        self.valid_resource_types = [
            ("elasticloadbalancing", "loadbalancer"),
            ("cloudfront", "distribution"),
            ("globalaccelerator", "accelerator"),
            ("route53", "hostedzone"),
            ("ec2", "eip-allocation"),
        ]
        arn_parts = parse_arn(resource_arn)
        resource_type = arn_parts.resource_type
        service = arn_parts.service
        if (service, resource_type) not in self.valid_resource_types:
            if resource_type:
                msg = f"Unrecognized resource '{resource_type}' of service '{service}'."
            else:
                msg = "Relative ID must be in the form '<resource>/<id>'."
            raise InvalidResourceException(msg)

    def create_protection(
        self, name: str, resource_arn: str, tags: list[dict[str, str]]
    ) -> str:
        for protection in self.protections.values():
            if protection.resource_arn == resource_arn:
                raise ResourceAlreadyExistsException(
                    "The referenced protection already exists."
                )
        self.validate_resource_arn(resource_arn)
        protection = Protection(
            account_id=self.account_id, name=name, resource_arn=resource_arn, tags=tags
        )
        self.protections[protection.protection_id] = protection
        self.tag_resource(protection.protection_arn, tags)
        return protection.protection_id

    def describe_protection(self, protection_id: str, resource_arn: str) -> Protection:  # type: ignore[return]
        if protection_id and resource_arn:
            msg = "Invalid parameter. You must provide one value, either protectionId or resourceArn, but not both."
            raise InvalidParameterException(msg)

        if resource_arn:
            for protection in self.protections.values():
                if protection.resource_arn == resource_arn:
                    return protection
            raise ResourceNotFoundException("The referenced protection does not exist.")

        if protection_id:
            if protection_id not in self.protections:
                raise ResourceNotFoundException(
                    "The referenced protection does not exist."
                )
            return self.protections[protection_id]

    def list_protections(self, inclusion_filters: dict[str, str]) -> list[Protection]:
        """
        Pagination has not yet been implemented
        """
        resource_protections = []
        name_protections = []
        type_protections = []

        if inclusion_filters:
            resource_arns = inclusion_filters.get("ResourceArns")
            if resource_arns:
                if len(resource_arns) > 1:
                    raise ValidationException(
                        "Error validating the following inputs: inclusionFilters.resourceArns"
                    )
                resource_protections = [
                    protection
                    for protection in self.protections.values()
                    if protection.resource_arn == resource_arns[0]
                ]
            protection_names = inclusion_filters.get("ProtectionNames")
            if protection_names:
                if len(protection_names) > 1:
                    raise ValidationException(
                        "Error validating the following inputs: inclusionFilters.protectionNames"
                    )
                name_protections = [
                    protection
                    for protection in self.protections.values()
                    if protection.name == protection_names[0]
                ]
            resource_types = inclusion_filters.get("ResourceTypes")
            if resource_types:
                if len(resource_types) > 1:
                    raise ValidationException(
                        "Error validating the following inputs: inclusionFilters.resourceTypes"
                    )
                type_protections = [
                    protection
                    for protection in self.protections.values()
                    if protection.resource_type == resource_types[0]
                ]
            try:
                protections = list(
                    set.intersection(
                        *(
                            set(x)
                            for x in [
                                resource_protections,
                                name_protections,
                                type_protections,
                            ]
                            if x
                        )
                    )
                )
            except TypeError:
                protections = []
        else:
            protections = list(self.protections.values())
        return protections

    def delete_protection(self, protection_id: str) -> None:
        if protection_id in self.protections:
            del self.protections[protection_id]
            return
        raise ResourceNotFoundException("The referenced protection does not exist.")

    def validate_protection_group(
        self, pattern: str, resource_type: str | None, members: list[str] | None
    ) -> None:
        """Raise exception if the pattern does not match the other arguments."""
        if pattern == "ARBITRARY":
            if not members:
                raise InvalidParameterException(
                    "Invalid parameter. You must specify Members when Pattern is ARBITRARY."
                )
            if resource_type:
                raise InvalidParameterException(
                    "Invalid parameter. You cannot specify ResourceType when Pattern is ARBITRARY."
                )
        elif pattern == "BY_RESOURCE_TYPE":
            if not resource_type:
                raise InvalidParameterException(
                    "Invalid parameter. You must specify ResourceType when Pattern is BY_RESOURCE_TYPE."
                )
            if members:
                raise InvalidParameterException(
                    "Invalid parameter. You cannot specify Members when Pattern is BY_RESOURCE_TYPE."
                )
        elif members or resource_type:
            raise InvalidParameterException(
                "Invalid parameter. You cannot specify Members or ResourceType when Pattern is ALL."
            )

    def create_protection_group(
        self,
        protection_group_id: str,
        aggregation: str,
        pattern: str,
        resource_type: str | None,
        members: list[str] | None,
        tags: list[dict[str, str]] | None,
    ) -> None:
        if protection_group_id in self.protection_groups:
            raise ResourceAlreadyExistsException(
                "The referenced protection group already exists."
            )
        self.validate_protection_group(pattern, resource_type, members)
        protection_group = ProtectionGroup(
            account_id=self.account_id,
            protection_group_id=protection_group_id,
            aggregation=aggregation,
            pattern=pattern,
            resource_type=resource_type,
            members=members,
        )
        self.protection_groups[protection_group_id] = protection_group
        if tags:
            self.tag_resource(protection_group.protection_group_arn, tags)

    def describe_protection_group(self, protection_group_id: str) -> ProtectionGroup:
        if protection_group_id not in self.protection_groups:
            raise ResourceNotFoundException(
                "The referenced protection group does not exist."
            )
        return self.protection_groups[protection_group_id]

    def update_protection_group(
        self,
        protection_group_id: str,
        aggregation: str,
        pattern: str,
        resource_type: str | None,
        members: list[str] | None,
    ) -> None:
        protection_group = self.describe_protection_group(protection_group_id)
        self.validate_protection_group(pattern, resource_type, members)
        protection_group.update(
            aggregation=aggregation,
            pattern=pattern,
            resource_type=resource_type,
            members=members,
        )

    def delete_protection_group(self, protection_group_id: str) -> None:
        self.describe_protection_group(protection_group_id)
        del self.protection_groups[protection_group_id]

    def list_protection_groups(
        self, inclusion_filters: dict[str, Any] | None
    ) -> list[ProtectionGroup]:
        """
        Pagination has not yet been implemented
        """
        protection_groups = list(self.protection_groups.values())
        if not inclusion_filters:
            return protection_groups

        filters = {
            "protectionGroupIds": ("ProtectionGroupIds", "protection_group_id"),
            "patterns": ("Patterns", "pattern"),
            "resourceTypes": ("ResourceTypes", "resource_type"),
            "aggregations": ("Aggregations", "aggregation"),
        }
        for input_name, (key, attribute) in filters.items():
            values = inclusion_filters.get(key)
            if not values:
                continue
            if len(values) > 1:
                raise ValidationException(
                    f"Error validating the following inputs: inclusionFilters.{input_name}"
                )
            protection_groups = [
                group
                for group in protection_groups
                if getattr(group, attribute) == values[0]
            ]
        return protection_groups

    def list_tags_for_resource(self, resource_arn: str) -> list[dict[str, str]]:
        return self.tagger.list_tags_for_resource(resource_arn)["Tags"]

    def tag_resource(self, resource_arn: str, tags: list[dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def create_subscription(self) -> None:
        self.subscription = Subscription(account_id=self.account_id)
        return

    def describe_subscription(self) -> Subscription:
        if self.subscription is None:
            raise ResourceNotFoundException("The subscription does not exist.")
        return self.subscription


shield_backends = BackendDict(
    ShieldBackend, "shield", additional_regions=PARTITION_NAMES
)
