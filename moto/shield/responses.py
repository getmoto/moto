"""Handles incoming shield requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import ShieldBackend, shield_backends


class ShieldResponse(BaseResponse):
    """Handler for Shield requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="shield")
        self.automated_parameter_parsing = True

    @property
    def shield_backend(self) -> ShieldBackend:
        """Return backend instance specific for this region."""
        return shield_backends[self.current_account][self.partition]

    def create_protection(self) -> ActionResult:
        name = self._get_param("Name")
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("Tags")
        protection_id = self.shield_backend.create_protection(
            name=name,
            resource_arn=resource_arn,
            tags=tags,
        )
        return ActionResult({"ProtectionId": protection_id})

    def describe_protection(self) -> ActionResult:
        protection_id = self._get_param("ProtectionId")
        resource_arn = self._get_param("ResourceArn")
        protection = self.shield_backend.describe_protection(
            protection_id=protection_id,
            resource_arn=resource_arn,
        )
        result = {
            "Protection": {
                "Id": protection.protection_id,
                "Name": protection.name,
                "ResourceArn": protection.resource_arn,
                "HealthCheckIds": protection.health_check_ids or None,
                "ProtectionArn": protection.protection_arn,
                "ApplicationLayerAutomaticResponseConfiguration": protection.application_layer_automatic_response_configuration
                or None,
            }
        }
        return ActionResult(result)

    def list_protections(self) -> ActionResult:
        inclusion_filters = self._get_param("InclusionFilters")
        protections = self.shield_backend.list_protections(
            inclusion_filters=inclusion_filters,
        )
        result: dict[str, Any] = {
            "Protections": [
                {
                    "Id": protection.protection_id,
                    "Name": protection.name,
                    "ResourceArn": protection.resource_arn,
                    "HealthCheckIds": protection.health_check_ids or None,
                    "ProtectionArn": protection.protection_arn,
                    "ApplicationLayerAutomaticResponseConfiguration": protection.application_layer_automatic_response_configuration
                    or None,
                }
                for protection in protections
            ]
        }
        return ActionResult(result)

    def delete_protection(self) -> ActionResult:
        protection_id = self._get_param("ProtectionId")
        self.shield_backend.delete_protection(
            protection_id=protection_id,
        )
        return EmptyResult()

    def create_protection_group(self) -> ActionResult:
        protection_group_id = self._get_param("ProtectionGroupId")
        aggregation = self._get_param("Aggregation")
        pattern = self._get_param("Pattern")
        resource_type = self._get_param("ResourceType")
        members = self._get_param("Members")
        tags = self._get_param("Tags")
        self.shield_backend.create_protection_group(
            protection_group_id=protection_group_id,
            aggregation=aggregation,
            pattern=pattern,
            resource_type=resource_type,
            members=members,
            tags=tags,
        )
        return EmptyResult()

    def describe_protection_group(self) -> ActionResult:
        protection_group_id = self._get_param("ProtectionGroupId")
        protection_group = self.shield_backend.describe_protection_group(
            protection_group_id=protection_group_id,
        )
        result = {
            "ProtectionGroup": {
                "ProtectionGroupId": protection_group.protection_group_id,
                "Aggregation": protection_group.aggregation,
                "Pattern": protection_group.pattern,
                "ResourceType": protection_group.resource_type,
                "Members": protection_group.members,
                "ProtectionGroupArn": protection_group.protection_group_arn,
            }
        }
        return ActionResult(result)

    def update_protection_group(self) -> ActionResult:
        protection_group_id = self._get_param("ProtectionGroupId")
        aggregation = self._get_param("Aggregation")
        pattern = self._get_param("Pattern")
        resource_type = self._get_param("ResourceType")
        members = self._get_param("Members")
        self.shield_backend.update_protection_group(
            protection_group_id=protection_group_id,
            aggregation=aggregation,
            pattern=pattern,
            resource_type=resource_type,
            members=members,
        )
        return EmptyResult()

    def delete_protection_group(self) -> ActionResult:
        protection_group_id = self._get_param("ProtectionGroupId")
        self.shield_backend.delete_protection_group(
            protection_group_id=protection_group_id,
        )
        return EmptyResult()

    def list_protection_groups(self) -> ActionResult:
        inclusion_filters = self._get_param("InclusionFilters")
        protection_groups = self.shield_backend.list_protection_groups(
            inclusion_filters=inclusion_filters,
        )
        result = {
            "ProtectionGroups": [
                {
                    "ProtectionGroupId": group.protection_group_id,
                    "Aggregation": group.aggregation,
                    "Pattern": group.pattern,
                    "ResourceType": group.resource_type,
                    "Members": group.members,
                    "ProtectionGroupArn": group.protection_group_arn,
                }
                for group in protection_groups
            ]
        }
        return ActionResult(result)

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceARN")
        tags = self.shield_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        return ActionResult({"Tags": tags})

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceARN")
        tags = self._get_param("Tags")
        self.shield_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceARN")
        tag_keys = self._get_param("TagKeys")
        self.shield_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        return EmptyResult()

    def create_subscription(self) -> ActionResult:
        self.shield_backend.create_subscription()
        return EmptyResult()

    def describe_subscription(self) -> ActionResult:
        subscription = self.shield_backend.describe_subscription()
        return ActionResult({"Subscription": subscription})
